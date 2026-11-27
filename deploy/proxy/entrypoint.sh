#!/bin/sh
# Nginx will not start on 443 until a certificate exists. Create a short-lived
# self-signed pair so the stack boots, then replace it with Let's Encrypt.
set -eu
CERT_DIR=/etc/nginx/certs
mkdir -p "$CERT_DIR" /var/www/certbot
if [ ! -s "$CERT_DIR/fullchain.pem" ] || [ ! -s "$CERT_DIR/privkey.pem" ]; then
  echo "mary-proxy: writing a temporary self-signed certificate for ${DOMAIN:-localhost}"
  openssl req -x509 -nodes -newkey rsa:2048 -days 2 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -subj "/CN=${DOMAIN:-localhost}"
fi
exec /docker-entrypoint.sh nginx -g "daemon off;"
