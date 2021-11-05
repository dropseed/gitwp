#!/bin/bash
set -eo pipefail

REPO_PATH=""

if [ -d "/repo_dev" ]
then
    echo "Found mounted repo at /repo_dev"
    REPO_PATH="/repo_dev"
fi

if [ -n "$GITHUB_WORKSPACE" ]
then
    echo "Found mounted GITHUB_WORKSPACE at $GITHUB_WORKSPACE"
    REPO_PATH="$GITHUB_WORKSPACE"
fi

if [ -z "$GITWP_TEST_PATH" ]
then
    echo "Adding $GITWP_TEST_PATH to repo path"
    REPO_PATH="$REPO_PATH/$GITWP_TEST_PATH"
    echo "Using repo path: $REPO_PATH"
fi

# An entire WordPress install is already available
if [ -d "$REPO_PATH/site" ]
then
    echo "Found entire site directory, setting apache root to $REPO_PATH/site"
    # https://hub.docker.com/_/php
    APACHE_DOCUMENT_ROOT="$REPO_PATH/site"
    sed -ri -e "s!/var/www/html!${APACHE_DOCUMENT_ROOT}!g" /etc/apache2/sites-available/*.conf
    sed -ri -e "s!/var/www/!${APACHE_DOCUMENT_ROOT}!g" /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

    # We'll move the original wp-config so we get a docker one, but we have to be
    # careful not to commit this change...
    echo "Deleting current wp-config.php to automatically create the docker version"
    rm -f "$REPO_PATH/site/wp-config.php"

    # Entrypoint expects to run from here
    cd "$REPO_PATH/site"
else
    # Entrypoint expects to run from here
    cd /var/www/html
fi

# Call the regular entrypoint
docker-entrypoint.sh apache2-foreground &
apache_pid=$!
sleep 2  # hacky - need part of their script to execute... (race condition)

# If we don't have a full site,
# assume we have plugins and themes, and symlink those for local development
if [ ! -d "$REPO_PATH/site" ]
then
    for d in plugins themes; do
        if [ -d "$REPO_PATH/$d" ]
        then
            echo "Linking development $d"
            for filename in /"$REPO_PATH"/"$d"/*; do
                BASENAME=$(basename "$filename")
                LINK=/var/www/html/wp-content/$d/$BASENAME
                echo "- $BASENAME"
                rm -rf "$LINK"
                ln -s "$filename" "$LINK"
            done
        fi
    done
fi

if [ -z "$*" ]; then
    # Wait on the foreground process
    wait "$apache_pid"
    # quit on ctrl c
    # trap "kill -TERM $pid" TERM INT
else
    # Exec whatever the user wanted
    exec "$@"
fi
