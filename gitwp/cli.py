from pathlib import Path
import click
from subprocess import check_call, run, PIPE
import yaml
import time


NETWORK_NAME = "gitwp"


def ensure_mysql():
    result = run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--network",
            NETWORK_NAME,
            "--platform",
            "linux/x86_64",
            "--name",
            "gitwp-mysql",
            "-p",
            "3306:3306",
            "-e",
            "MYSQL_DATABASE=wordpress",
            "-e",
            "MYSQL_ROOT_PASSWORD=pass",
            "mysql:5.7",
        ]
    )

    if result.returncode == 125:
        # Already in use
        return

    if result.returncode != 0:
        raise Exception("Failed to start mysql container")


def ensure_proxy():
    if not Path("/etc/resolver/gitwp").exists():
        click.secho("Creating /etc/resolver/gitwp (may have to enter your password)", fg="green")
        run(
            """sudo mkdir -p /etc/resolver && sudo tee /etc/resolver/gitwp >/dev/null <<EOF
nameserver 127.0.0.1
port 54
EOF""", shell=True
        )

    result = run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--network",
            NETWORK_NAME,
            "--name",
            "gitwp-proxy",
            "-p",
            "80:80",
            "-p",
            "443:443",
            "-p",
            "54:54",
            "-p",
            "54:54/udp",
            "gitwp-proxy",
        ],
        stdout=PIPE,
        stderr=PIPE,
    )

    if result.returncode != 0 and f"network {NETWORK_NAME} not found" in result.stderr.decode():
        click.secho("Creating network", fg="green")
        check_call(["docker", "network", "create", NETWORK_NAME])
        return ensure_proxy()

    # This doesn't work right
    if result.returncode == 125:
        # Already in use
        return

    if result.returncode != 0:
        raise Exception("Failed to start proxy container")


def build_gitwp():
    check_call(
        ["docker", "build", "-t", "gitwp", "."],
        # TODO docker should be in gitwp dir
        cwd=str(Path(__file__).parent.parent / "docker"),
    )
    check_call([
        "docker", "build", "-t", "gitwp-proxy", "."
    ], cwd=str(Path(__file__).parent.parent / "proxy"))


def run_container(project_path: Path, container_name: str, db_name: str):
    db_user = "root"
    db_password = "pass"

    result = run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--network",
            NETWORK_NAME,
            "--name",
            container_name,
            # "-p",
            # "80:80",
            # "-p",
            # "443:443",
            "-v",
            f"{project_path.absolute()}:/repo_dev",
            # "-e",
            # "MYSQL_HOST=gitwp-mysql",
            "-e",
            "WORDPRESS_DB_HOST=gitwp-mysql",
            "-e",
            f"WORDPRESS_DB_USER={db_user}",
            "-e",
            f"WORDPRESS_DB_PASSWORD={db_password}",
            "-e",
            f"WORDPRESS_DB_NAME={db_name}",
            "gitwp",
        ]
    )
    if result.returncode == 125:
        check_call(["docker", "stop", container_name])
        # check_call([
        #     'docker', 'rm', container_name
        # ])
        run_container(project_path, container_name, db_name)


class MissingConfigError(Exception):
    pass


def load_config(project_path: Path):
    try:
        with open(project_path / "gitwp.yml") as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise MissingConfigError("gitwp.yml not found") from e


class HostType:
    pass


class SSHHost(HostType):
    def __init__(
        self,
        hostname: str,
        username: str,
        repo_path: Path,
        site_path: Path,
        wpcli: Path,
    ):
        self.hostname = hostname
        self.username = username
        self.repo_path = repo_path
        self.site_path = site_path
        self.wpcli = wpcli

    def sync_db(self, download_to: Path) -> Path:
        ssh_host = f"{self.username}@{self.hostname}"
        dump_path = self.repo_path / "db_dump" / "db.sql"  # TODO change to .bolt later
        check_call(
            [
                "ssh",
                ssh_host,
                f"{self.wpcli} db export --path={self.site_path} --porcelain {dump_path} && gzip -f {dump_path}",
            ]
        )
        dump_path = dump_path.with_suffix(".sql.gz")
        check_call(
            [
                "rsync",
                "-avH",
                "--delete",
                "-e",
                "ssh",
                f"{ssh_host}:{dump_path}",
                str(download_to) + "/",
            ]
        )
        return download_to / dump_path.name


@click.group()
def cli():
    pass


@click.option("--build", is_flag=True)
@click.option("--sync", is_flag=True)
@cli.command()
def work(sync: bool, build: bool):
    if build:
        # TODO a way to check if needed?
        click.secho("Building gitwp image", fg="green")
        build_gitwp()

    click.secho("Ensuring proxy", fg="green")
    ensure_proxy()
    click.secho("Ensuring mysql", fg="green")
    ensure_mysql()

    # use mysql healthcheck...

    project_path = Path.cwd()
    project_name = project_path.name.lower()
    container_name = f"gitwp-{project_name}"

    run_container(
        project_path=project_path,
        container_name=container_name,
        db_name=project_name,
    )

    dev_domain = f"{project_name}.dev.gitwp"

    if sync:
        dotbolt_path = project_path / ".bolt"
        if not dotbolt_path.exists():
            dotbolt_path.mkdir()
        dotbolt_gitignore = dotbolt_path / ".gitignore"
        if not dotbolt_gitignore.exists():
            dotbolt_gitignore.write_text("*\n")

        config = load_config(project_path)
        host_type = config["host"]["type"]
        if host_type == "ssh":
            host = SSHHost(
                hostname=config["host"]["hostname"],
                username=config["host"]["username"],
                repo_path=Path(config["host"]["repo_path"]),
                site_path=Path(config["host"]["site_path"]),
                wpcli=Path(config["host"]["wpcli"]),
            )
        else:
            raise ValueError(f"Unknown host type: {host_type}")

        click.secho(f"Syncing database from {host_type} host", fg="green")
        # db_path = host.sync_db(dotbolt_path)  # TODO change to .bolt later
        # db_path = db_path.relative_to(project_path)
        db_path = Path(".bolt/db.sql.gz")

        click.secho(f"Loading database into container", fg="green")
        check_call(
            [
                "docker",
                "exec",
                "-i",
                container_name,
                # "bash", "-c", "ls /site"
                "bash",
                "-c",
                f"wp --allow-root --path=/site db create; gunzip -c /repo_dev/{db_path} | wp --allow-root --path=/site db import -",
            ]
        )

        click.secho("Replacing URLs", fg="green")
        check_call(
            [
                "docker",
                "exec",
                "-i",
                container_name,
                "wp",
                "--allow-root",
                "--path=/site",
                "search-replace",
                "--all-tables",
                config["domain"],
                dev_domain,
            ]
        )

    click.secho(f"Working on http://{dev_domain}", fg="green")

    try:
        run(["docker", "logs", "-f", container_name])
    except KeyboardInterrupt:
        run(["docker", "stop", container_name])


@cli.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.argument("wp_args", nargs=-1, type=click.UNPROCESSED)
def wp(wp_args):
    project_path = Path.cwd()
    project_name = project_path.name.lower()
    container_name = f"gitwp-{project_name}"

    run(
        [
            "docker",
            "exec",
            "-e",
            "PAGER=cat",
            "-it",
            container_name,
            "wp",
            "--allow-root",
            "--path=/site",
        ]
        + list(wp_args)
    )


@cli.command()
def stop():
    project_path = Path.cwd()
    project_name = project_path.name.lower()
    container_name = f"gitwp-{project_name}"

    containers = [
        container_name,
        f"gitwp-mysql",
        f"gitwp-proxy",
    ]
    run(["docker", "stop"] + containers)
