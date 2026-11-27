#!/bin/sh
# Renew the Let's Encrypt certificate and reload Nginx when a new file is issued.
# Install on the droplet as /var/mary/mary-documents/production-deployment/templates/renew-certificate.sh
# or copy it to /usr/local/sbin/mary-renew-certificate.
# Cron: 20 3 * * * /path/to/renew-certificate.sh >> /var/log/mary-certbot.log 2>&1
set -eu

cd /var/mary
DOMAIN="${DOMAIN:-registryv2.stmarysteamcare.co.uk}"

docker compose --env-file .env.production -f docker-compose.prod.yml --profile tls run --rm certbot renew --quiet

docker compose --env-file .env.production -f docker-compose.prod.yml exec -T proxy \
  sh -c "cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /etc/nginx/certs/fullchain.pem && cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem /etc/nginx/certs/privkey.pem && nginx -s reload"
