#!/bin/bash
# scripts/gen_selfsigned_cert.sh
# Generates a self-signed SSL certificate for IP-based deployments.
# Run this BEFORE starting nginx.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
CERT_DIR="$REPO_DIR/nginx/certs"

# Load DOMAIN from .env
source "$REPO_DIR/.env"

mkdir -p "$CERT_DIR"

openssl req -x509 -newkey rsa:4096 -nodes -days 825 \
  -keyout "$CERT_DIR/selfsigned.key" \
  -out    "$CERT_DIR/selfsigned.crt" \
  -subj   "/CN=${DOMAIN}" \
  -addext "subjectAltName=IP:${DOMAIN}" 2>/dev/null || \
openssl req -x509 -newkey rsa:4096 -nodes -days 825 \
  -keyout "$CERT_DIR/selfsigned.key" \
  -out    "$CERT_DIR/selfsigned.crt" \
  -subj   "/CN=${DOMAIN}"

chmod 600 "$CERT_DIR/selfsigned.key"
chmod 644 "$CERT_DIR/selfsigned.crt"

echo "Self-signed certificate generated:"
echo "  $CERT_DIR/selfsigned.crt"
echo "  $CERT_DIR/selfsigned.key"
echo ""
echo "Register Telegram webhook with this cert:"
echo "  curl -X POST \"https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/setWebhook\" \\"
echo "    -F \"url=https://\${DOMAIN}/telegram-webhook\" \\"
echo "    -F \"certificate=@$CERT_DIR/selfsigned.crt\""
