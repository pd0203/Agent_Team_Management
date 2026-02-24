#!/bin/bash
# ============================================================
# scripts/certbot_setup.sh — Standalone SSL certificate setup.
# Run this on the server AFTER pointing your domain DNS to the
# server IP, and AFTER starting Nginx for the first time.
# ============================================================
set -euo pipefail

set -a; source "$(dirname "$0")/../.env"; set +a

echo "Obtaining Let's Encrypt certificate for: ${DOMAIN}"

docker compose run --rm certbot \
    certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "${DOMAIN}" \
    --email "admin@${DOMAIN}" \
    --agree-tos \
    --non-interactive

echo "Certificate obtained. Reloading Nginx..."
docker compose exec nginx nginx -s reload

echo "Done! SSL is active for ${DOMAIN}."
