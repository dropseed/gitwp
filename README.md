# gitwp-tests

Runs some basic tests against a WordPress installation for plugin or theme errors.

What it does:

- installs WordPress
- activates themes
- activates plugins
- pings the homepage and checks for errors in debug log
- pings the login page and checks for errors in debug log

## gitwp.yml

You can configure the tests by adding `gitwp.yml` to the root of your repo.
Here's an example of the options:

```yaml
tests:
  enabled: true
  after_wp_install: echo 'hook after_wp_install'
  before_test: echo 'hook before_test'
  after_test: echo 'hook after_test'
  test_wp_home_url:
    ignore_logs: [FOOBAR]
  test_wp_login_url:
    enabled: false
```

## GitHub Actions

Here's an example of how to use the GitHub Action with a basic mysql setup:

```yaml
name: gitwp test

on: push

jobs:
  test-deploy:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:5.7
        ports: ["3306:3306"]
        env:
          MYSQL_ALLOW_EMPTY_PASSWORD: yes
          MYSQL_DATABASE: wordpress
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=5
    steps:
    - uses: actions/checkout@v2
    - name: test
      uses: dropseed/gitwp@v1
```
