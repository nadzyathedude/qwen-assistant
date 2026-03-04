#!/usr/bin/env bash
# Qwen Assistant VPS Setup Script (CPU-only)
# Run this script on your Ubuntu/Debian VPS

set -euo pipefail

echo "=== Qwen Assistant VPS Deployment ==="
echo ""

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

step() {
    echo -e "${GREEN}>>> $1${NC}"
}

warn() {
    echo -e "${YELLOW}!!! $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   warn "This script should NOT be run as root (use sudo within the script)"
   exit 1
fi

step "1. Installing system dependencies..."
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    ufw \
    curl \
    wget

step "2. Building llama.cpp (CPU-only)..."
if [ ! -d "/opt/llama.cpp" ]; then
    sudo mkdir -p /opt
    cd /opt
    sudo git clone https://github.com/ggerganov/llama.cpp.git
    cd llama.cpp
    sudo cmake -B build
    sudo cmake --build build --config Release -j$(nproc)
    echo "llama.cpp built at: /opt/llama.cpp/build/bin/llama-cli"
else
    warn "llama.cpp already exists at /opt/llama.cpp - skipping"
fi

step "3. Downloading Qwen model (Q4_K_M - 4GB)..."
sudo mkdir -p /opt/qwen-assistant/models
if [ ! -f "/opt/qwen-assistant/models/qwen.gguf" ]; then
    cd /opt/qwen-assistant/models
    warn "Downloading 4GB model file... this will take several minutes"
    sudo wget -O qwen.gguf \
        https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
    echo "Model downloaded to: /opt/qwen-assistant/models/qwen.gguf"
else
    warn "Model already exists - skipping download"
fi

step "4. Setting up application directory..."
if [ ! -d "/opt/qwen-assistant/.git" ]; then
    warn "Please clone your repository to /opt/qwen-assistant manually:"
    echo "  sudo git clone <your-repo-url> /opt/qwen-assistant"
    exit 1
fi

cd /opt/qwen-assistant

step "5. Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    sudo python3 -m venv venv
    sudo chown -R $USER:$USER venv
fi

source venv/bin/activate
pip install -r requirements.txt

step "6. Configuring .env file..."
if [ ! -f ".env" ]; then
    sudo cp .env.example .env
    # Generate API token
    API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    sudo tee .env > /dev/null <<EOF
# llama.cpp binary path
LLAMA_CPP_PATH=/opt/llama.cpp/build/bin/llama-cli

# Model file path
MODEL_PATH=/opt/qwen-assistant/models/qwen.gguf

# API authentication token
API_TOKEN=${API_TOKEN}

# Server configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Model settings (CPU-optimized)
THREADS=$(nproc)
CTX_SIZE=4096
GPU_LAYERS=0

# System prompt (optional)
SYSTEM_PROMPT=You are a helpful assistant. Answer concisely and accurately.
EOF

    warn "Generated API token: ${API_TOKEN}"
    echo "Save this token! You'll need it to authenticate API requests."
else
    warn ".env already exists - skipping"
fi

step "7. Creating system user..."
if ! id -u qwen > /dev/null 2>&1; then
    sudo useradd -r -s /bin/false -d /opt/qwen-assistant qwen
fi
sudo chown -R qwen:qwen /opt/qwen-assistant

step "8. Installing systemd service..."
sudo cp deploy/qwen-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable qwen-server
sudo systemctl start qwen-server

step "9. Checking service status..."
sleep 2
sudo systemctl status qwen-server --no-pager || true

step "10. Configuring nginx..."
sudo cp deploy/nginx.conf /etc/nginx/sites-available/qwen-server
sudo ln -sf /etc/nginx/sites-available/qwen-server /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

step "11. Configuring firewall..."
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Next steps:"
echo "1. Point your domain to this server's IP address"
echo "2. Set up HTTPS with Let's Encrypt:"
echo "   sudo apt install certbot python3-certbot-nginx"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo "3. Test the deployment:"
echo "   curl http://$(curl -s ifconfig.me)/health"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u qwen-server -f"
echo ""
warn "API Token: ${API_TOKEN}"
echo "Keep this token secure!"
