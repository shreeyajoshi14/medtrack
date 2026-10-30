#!/usr/bin/env bash
# =========================================================
# MEDTRACK - AWS EC2 PRODUCTION SETUP SCRIPT
# Provisions Python 3, Gunicorn, Nginx, and systemd service
# as specified in the MedTrack Cloud Architecture.
# =========================================================

set -e

echo "=== 1. Updating System Packages & Installing Nginx, Python ==="
if [ -f /etc/debian_version ]; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-pip python3-venv git nginx
elif [ -f /etc/redhat-release ]; then
    sudo dnf update -y
    sudo dnf install -y python3 python3-pip git nginx
fi

echo "=== 2. Setting Up Python Virtual Environment ==="
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 3. Creating systemd Service for Gunicorn ==="
APP_DIR=$(pwd)
CURRENT_USER=$(whoami)

sudo tee /etc/systemd/system/medtrack.service > /dev/null <<EOF
[Unit]
Description=MedTrack Flask Healthcare Platform
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "=== 4. Configuring Nginx Reverse Proxy (Port 80) ==="
if [ -d "/etc/nginx/sites-available" ]; then
    sudo tee /etc/nginx/sites-available/medtrack > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo ln -sf /etc/nginx/sites-available/medtrack /etc/nginx/sites-enabled/
else
    # RedHat / Amazon Linux configuration
    sudo tee /etc/nginx/conf.d/medtrack.conf > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
fi

echo "=== 5. Starting MedTrack Service & Nginx ==="
sudo systemctl daemon-reload
sudo systemctl enable medtrack
sudo systemctl restart medtrack

sudo systemctl enable nginx
sudo systemctl restart nginx

echo ""
echo "========================================================="
echo "  MedTrack Cloud Deployment is COMPLETE!"
echo "  - Nginx Reverse Proxy listening on HTTP Port 80"
echo "  - Gunicorn WSGI listening on 127.0.0.1:5000"
echo "  - DynamoDB Tables: UsersTable, AppointmentsTable"
echo "  - AWS SNS Topic: MedTrack_Notifications"
echo "  Access live at: http://<EC2-PUBLIC-IP>/"
echo "========================================================="
