ARG WP_VERSION=5.8.1
ARG PHP_VERSION=7.4
FROM wordpress:${WP_VERSION}-php${PHP_VERSION}-apache

# Clear out the base plugins
RUN rm -r /usr/src/wordpress/wp-content/plugins
COPY plugins /usr/src/wordpress/wp-content/plugins

# Clear out the base themes
RUN rm -r /usr/src/wordpress/wp-content/themes
COPY themes /usr/src/wordpress/wp-content/themes

# TODO install base plugins from yml

# if repo is rsynced first, and part of build, copy stuff DIRECTLY into base
# COPY repo/plugins /usr/src/wordpress/wp-content/plugins
# COPY repo/themes /usr/src/wordpress/wp-content/themes

# VOLUME ["/repo_dev"]

EXPOSE 80
EXPOSE 443

RUN curl -sL https://github.com/mikefarah/yq/releases/download/v4.14.1/yq_linux_amd64.tar.gz -o /tmp/yq.tar.gz \
    && tar -xzf /tmp/yq.tar.gz -C /usr/local/bin \
    && mv /usr/local/bin/yq_linux_amd64 /usr/local/bin/yq

# TODO version as build arg
RUN curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && php wp-cli.phar --info && chmod +x wp-cli.phar && mv wp-cli.phar /usr/local/bin/wp

COPY gitwp-entrypoint.sh /usr/local/bin/
COPY test /usr/local/bin/

ENTRYPOINT ["gitwp-entrypoint.sh"]
