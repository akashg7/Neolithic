#!/bin/sh
# Runs inside the nginx container before nginx starts (official image hook).
# Picks HTTP or HTTPS server blocks, then reloads nginx twice a day so a
# renewed certificate is picked up without a restart.
set -e
mkdir -p /etc/nginx/km-active /var/www/certbot
CERT="/etc/letsencrypt/live/${DOMAIN:-none}/fullchain.pem"
if [ -n "${DOMAIN:-}" ] && [ -f "$CERT" ]; then
  sed "s/__DOMAIN__/${DOMAIN}/g" /etc/nginx/km/servers-https.conf > /etc/nginx/km-active/servers.conf
  echo "krishimitr: HTTPS for ${DOMAIN}"
else
  cp /etc/nginx/km/servers-http.conf /etc/nginx/km-active/servers.conf
  echo "krishimitr: HTTP only (no certificate for '${DOMAIN:-}' yet)"
fi
( while sleep 43200; do nginx -s reload 2>/dev/null || true; done ) &
