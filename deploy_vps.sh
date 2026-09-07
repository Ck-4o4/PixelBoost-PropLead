#!/usr/bin/env bash
# ==============================================================================
# PropLeads AI — 1-Click Hostinger VPS Automated Deployment Script
# Supports: Ubuntu 20.04 / 22.04 / 24.04 LTS
# ==============================================================================

set -e

echo "========================================================="
echo " 🚀 PropLeads AI — Hostinger VPS Automated Setup"
echo " Made with ❤️ By CK"
echo "========================================================="

# 1. Update System
echo "📦 [1/6] Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl nginx certbot python3-certbot-nginx

# 2. Setup App Directory
APP_DIR="/var/www/propleads"
echo "📁 [2/6] Setting up project directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# Copy or clone files here
if [ ! -f "$APP_DIR/app.py" ]; then
    cp -r ./* $APP_DIR/ || true
fi

cd $APP_DIR

# 3. Setup Python Virtual Environment
echo "🐍 [3/6] Setting up Python virtual environment & Playwright..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browser and system libraries
playwright install-deps chromium
playwright install chromium

# 4. Create Systemd Background Service
echo "⚙️ [4/6] Creating systemd service (propleads.service)..."
sudo bash -c "cat <<EOF > /etc/systemd/system/propleads.service
[Unit]
Description=PropLeads AI Lead Scraper & Calling CRM
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable propleads
sudo systemctl restart propleads

# 5. Configure Nginx Reverse Proxy
echo "🌐 [5/6] Configuring Nginx reverse proxy..."
read -p "Enter your domain name (e.g., leads.yourdomain.com or yourdomain.com): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    DOMAIN_NAME="_"
fi

sudo bash -c "cat <<EOF > /etc/nginx/sites-available/propleads
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \\\$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;

        # Real-Time SSE Stream support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        chunked_transfer_encoding on;
    }
}
EOF"

sudo ln -sf /etc/nginx/sites-available/propleads /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default || true
sudo nginx -t
sudo systemctl restart nginx

# 6. SSL Certificate
if [ "$DOMAIN_NAME" != "_" ]; then
    echo "🔒 [6/6] Generating Free SSL Certificate via Let's Encrypt..."
    read -p "Do you want to install free SSL HTTPS certificate now? (y/n): " INSTALL_SSL
    if [ "$INSTALL_SSL" = "y" ] || [ "$INSTALL_SSL" = "Y" ]; then
        sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos -m admin@$DOMAIN_NAME || true
    fi
fi

echo "========================================================="
echo " 🎉 Deployment Complete!"
echo " 🌐 Your App is Live at: http://$DOMAIN_NAME"
echo " 🛠 Manage service: sudo systemctl status propleads"
echo "========================================================="
