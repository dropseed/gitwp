FROM nginx

# so we can test ping to container names
RUN apt-get update && apt-get install -y iputils-ping dnsmasq

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY certs /etc/ssl/certs

CMD ["/bin/sh", "-c", "dnsmasq -dq --port=54 --no-resolv --no-hosts --address=/#/127.0.0.1 --address=/#/::1 & nginx-debug -g 'daemon off;'"]
