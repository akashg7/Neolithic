#!/bin/sh
# Certificate renewer (certbot container). Renews when within 30 days of
# expiry; nginx reloads itself twice a day to pick the new one up.
trap 'exit 0' TERM INT
while true; do
  certbot renew --webroot -w /var/www/certbot --quiet
  sleep 43200 &
  wait "$!"
done
