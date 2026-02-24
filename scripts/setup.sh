#!/bin/bash
# ============================================================
# scripts/setup.sh — Oracle Cloud A1.Flex initial setup
# Ubuntu 22.04 ARM64
# ============================================================
set -euo pipefail

echo "=== Hyojin Distribution AI Agent Team Setup ==="
echo "Platform: OpenClaw (https://github.com/openclaw/openclaw)"

# 1. System update
echo ">>> [1/6] System update..."
sudo apt-get update -qq && sudo apt-get upgrade -y -qq

# 2. Docker
echo ">>> [2/6] Installing Docker..."
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    newgrp docker
fi
echo "Docker: $(docker --version)"
echo "Docker Compose: $(docker compose version)"

# 3. .env setup
echo ">>> [3/6] Configuring .env..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

if [ ! -f .env ]; then
    cp .env.example .env
    # Auto-generate secrets
    sed -i "s/replace_with_openssl_rand_hex_32/$(openssl rand -hex 32)/" .env
    sed -i "s/replace_with_strong_password/$(openssl rand -base64 32 | tr -d '/+=')/" .env
    echo ""
    echo ">>> Please fill in .env:"
    echo "    TELEGRAM_BOT_TOKEN, CEO_TELEGRAM_ID, GEMINI_API_KEY, DOMAIN"
    echo ""
    read -p "Edit .env now? (will open nano) [y/N]: " EDIT
    [[ "$EDIT" =~ ^[Yy]$ ]] && nano .env
fi

source .env

# 4. Nginx domain substitution
echo ">>> [4/6] Nginx config for domain: ${DOMAIN}"
sed -i "s/DOMAIN/${DOMAIN}/g" nginx/nginx.conf

# 5. Firewall
echo ">>> [5/6] Firewall..."
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
sudo apt-get install -y iptables-persistent -qq
sudo netfilter-persistent save

# 6. SSL + start
echo ">>> [6/6] SSL certificate + start services..."
echo ""
read -p "Get Let's Encrypt cert for ${DOMAIN}? (DNS must point here) [y/N]: " SSL
if [[ "$SSL" =~ ^[Yy]$ ]]; then
    docker compose up -d nginx certbot
    sleep 3
    docker compose run --rm certbot certbot certonly \
        --webroot -w /var/www/certbot \
        -d "${DOMAIN}" \
        --email "admin@${DOMAIN}" \
        --agree-tos --non-interactive
    docker compose exec nginx nginx -s reload
fi

docker compose up -d --build

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Set Telegram webhook:"
echo "     curl -X POST https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/setWebhook \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"url\": \"https://\${DOMAIN}/telegram-webhook\"}'"
echo ""
echo "  2. Send a message to your bot on Telegram"
echo ""
echo "  3. Monitor logs: docker compose logs -f openclaw-gateway"
echo "                   docker compose logs -f budget-guard"
