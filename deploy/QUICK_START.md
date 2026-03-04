# Quick Start Deployment Guide

## Prerequisites
- Ubuntu 22.04+ or Debian 12+ VPS with **6GB+ RAM**
- Root or sudo access
- Domain name (optional but recommended)

## Option 1: Automated Deployment (Recommended)

### 1. On your local machine, push code to Git repository:
```bash
# If you haven't already, initialize git repo
cd /Users/nadzya/qwen-assistant
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-git-url>
git push -u origin main
```

### 2. SSH into your VPS:
```bash
ssh root@your-vps-ip
# or: ssh your-user@your-vps-ip
```

### 3. Clone the repository:
```bash
sudo mkdir -p /opt
cd /opt
sudo git clone <your-repo-url> qwen-assistant
cd qwen-assistant
```

### 4. Run the automated setup script:
```bash
chmod +x deploy/setup_vps.sh
./deploy/setup_vps.sh
```

The script will:
- Install all dependencies
- Build llama.cpp (CPU-only)
- Download Qwen 7B model (~4GB)
- Set up Python environment
- Generate API token
- Create systemd service
- Configure nginx
- Set up firewall

### 5. Set up HTTPS (if you have a domain):
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com
```

### 6. Test the deployment:
```bash
# Health check
curl http://your-vps-ip/health
# or with domain: curl https://your-domain.com/health

# Should return: {"status":"ok"}
```

### 7. Test generation (replace YOUR_TOKEN with the token from step 4):
```bash
curl -N -X POST http://your-vps-ip/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is Python?",
    "max_tokens": 128,
    "temperature": 0.7,
    "stream": false
  }'
```

## Option 2: Manual Deployment

Follow the detailed instructions in `deploy.md`

## Monitoring

```bash
# View real-time logs
sudo journalctl -u qwen-server -f

# Check service status
sudo systemctl status qwen-server

# Restart service
sudo systemctl restart qwen-server

# Check memory usage
free -h
ps aux | grep llama-cli
```

## Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 6 GB | 8 GB |
| CPU | 2 cores | 4+ cores |
| Disk | 10 GB | 20 GB |
| Bandwidth | 100 Mbps | 1 Gbps |

## VPS Provider Recommendations

**Budget-friendly (CPU-only):**
- **Hetzner** CPX31: 8 GB RAM, 4 vCPU, ~$13/month
- **DigitalOcean** Basic 8GB: 8 GB RAM, 4 vCPU, ~$48/month
- **Vultr** High Frequency 8GB: 8 GB RAM, 4 vCPU, ~$48/month

**Performance (GPU):**
- **RunPod**: GPU instances starting ~$0.20/hour
- **Vast.ai**: GPU instances starting ~$0.10/hour

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u qwen-server -n 100 --no-pager

# Common issues:
# 1. Wrong paths in .env
# 2. Missing model file
# 3. Permissions issues
```

### Model download failed
```bash
# Re-download model manually
cd /opt/qwen-assistant/models
sudo wget -O qwen.gguf \
  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf
```

### Nginx configuration errors
```bash
# Test nginx config
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

## Security Notes

1. **Never expose port 8000** directly - use nginx as reverse proxy
2. **Use strong API tokens** - generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
3. **Enable firewall** - only allow ports 22, 80, 443
4. **Use HTTPS** - set up Let's Encrypt SSL certificate
5. **Keep tokens secret** - don't commit .env to git

## Next Steps

After deployment:
1. Set up monitoring (uptime checks, resource alerts)
2. Configure backups for your models and data
3. Set up log rotation
4. Consider adding rate limiting
5. Set up a load balancer for multiple instances (if needed)
