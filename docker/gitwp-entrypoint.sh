#!/bin/bash
set -eo pipefail

ARGS="$*@"

# if not args
if [ -z "$ARGS" ]; then
    # Call the regular entrypoint
    docker-entrypoint.sh apache2-foreground &
    pid=$!

    sleep 2  # hacky - need part of their script to execute... (race condition)
fi

MOUNTED_PLUGINS_THEMES_PATH=""

if [ -d "/repo_dev" ]
then
    echo "Found mounted repo at /repo_dev"
    MOUNTED_PLUGINS_THEMES_PATH="/repo_dev"
fi

if [ -n "$GITHUB_WORKSPACE" ]
then
    echo "Found mounted GITHUB_WORKSPACE at $GITHUB_WORKSPACE"
    MOUNTED_PLUGINS_THEMES_PATH="$GITHUB_WORKSPACE"
fi

# Hack for now...
if [ -d "$MOUNTED_PLUGINS_THEMES_PATH/site" ]
then
    echo "Found entire site directory, linking plugins/themes from site/wp-content"
    MOUNTED_PLUGINS_THEMES_PATH="$MOUNTED_PLUGINS_THEMES_PATH/site/wp-content"
fi
# endhack

# Or just use the plugins and themes dirs from the root
# repo/plugins, repo/themes
for d in plugins themes; do
    if [ -d "$MOUNTED_PLUGINS_THEMES_PATH/$d" ]
    then
        echo "Linking development $d"
        for filename in /"$MOUNTED_PLUGINS_THEMES_PATH"/"$d"/*; do
            BASENAME=$(basename "$filename")
            LINK=/var/www/html/wp-content/$d/$BASENAME
            echo "- $BASENAME"
            rm -rf "$LINK"
            ln -s "$filename" "$LINK"
        done
    fi
done

if [ -z "$ARGS" ]; then
    # Wait on the foreground process
    wait "$pid"
else
    # Exec whatever the user wanted
    exec "$@"
fi
