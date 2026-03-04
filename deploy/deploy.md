# Deployment Guide

## 1. Prerequisites

- Ubuntu 22.04+ or Debian 12+ VPS
- Python 3.10+
- cmake, build-essential (for llama.cpp)
- NVIDIA GPU + CUDA toolkit (optional, for GPU inference)

## 2. Build llama.cpp

```bash
cd /opt
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
```

**CPU-only build:**

```bash
cmake -B build
cmake --build build --config Release -j$(nproc)
```

**CUDA GPU build:**

```bash
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j$(nproc)
```

The binary is at `build/bin/llama-cli`.

## 3. Download Qwen Model (GGUF)

Download a quantized Qwen model from Hugging Face. Recommended quantization levels:

| Quantization | RAM Required | Quality   | Recommended For            |
|-------------|-------------|-----------|----------------------------|
| Q4_K_M      | ~4 GB       | Good      | Most VPS setups            |
| Q5_K_M      | ~5 GB       | Very good | VPS with 8+ GB RAM         |
| Q6_K        | ~6 GB       | Excellent | VPS with 12+ GB RAM        |
| Q8_0        | ~8 GB       | Near-FP16 | GPU or high-RAM machines   |

Example (Qwen2.5-7B Q4_K_M):

```bash
mkdir -p /opt/qwen-assistant/models
cd /opt/qwen-assistant/models
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf \
     -O qwen.gguf
```

## 4. Install the Application

```bash
cd /opt
git clone <your-repo-url> qwen-assistant
cd qwen-assistant

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your paths and settings
```

Update `.env` with actual paths:

```
LLAMA_CPP_PATH=/opt/llama.cpp/build/bin/llama-cli
MODEL_PATH=/opt/qwen-assistant/models/qwen.gguf
API_TOKEN=<generate-a-strong-random-token>
```

Generate a strong token:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 5. Create System User

```bash
sudo useradd -r -s /bin/false -d /opt/qwen-assistant qwen
sudo chown -R qwen:qwen /opt/qwen-assistant
```

## 6. Install systemd Service

```bash
sudo cp deploy/qwen-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable qwen-server
sudo systemctl start qwen-server

# Check status
sudo systemctl status qwen-server
sudo journalctl -u qwen-server -f
```

## 7. Configure nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/qwen-server
sudo ln -s /etc/nginx/sites-available/qwen-server /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Set up HTTPS with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 8. Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Do NOT expose port 8000 publicly — nginx handles external traffic
```

## 9. Test the Deployment

Health check:

```bash
curl https://your-domain.com/health
```

Streaming generation:

```bash
curl -N -X POST https://your-domain.com/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms.",
    "max_tokens": 256,
    "temperature": 0.7,
    "stream": true
  }'
```

Non-streaming generation:

```bash
curl -X POST https://your-domain.com/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is Python?",
    "max_tokens": 128,
    "stream": false
  }'
```

## 10. Resource Monitoring

```bash
# Real-time process monitoring
htop

# GPU monitoring (if CUDA)
watch -n1 nvidia-smi

# Memory usage of inference processes
ps aux | grep llama-cli

# Disk usage for models
du -sh /opt/qwen-assistant/models/

# Journal log monitoring
journalctl -u qwen-server -f --no-pager
```

## 11. Performance Tuning

### CPU inference

- Set `THREADS` to the number of physical cores (not hyperthreads).
- Use `Q4_K_M` quantization for best speed/quality balance.
- Set `CTX_SIZE` only as large as needed — larger context = more RAM + slower.

### GPU inference

- Set `GPU_LAYERS=-1` to offload all layers to GPU.
- Partial offload: set `GPU_LAYERS` to the number of layers that fit in VRAM.
  Run `llama-cli` with `--verbose` to see per-layer VRAM requirements.
- For 7B models: ~6 GB VRAM for full Q4_K_M offload.

### Memory optimization

- Qwen 7B Q4_K_M uses ~4 GB RAM for weights + ~1 GB for context.
- Reduce `CTX_SIZE` from 4096 to 2048 to save ~500 MB.
- Use `Q4_0` instead of `Q4_K_M` for ~15% less RAM (minor quality loss).
- Avoid concurrent requests on limited hardware — the systemd service runs
  one process, and each request spawns one llama-cli subprocess.

### VPS sizing

| Model Size | Quantization | Minimum VPS RAM |
|-----------|-------------|-----------------|
| 1.5B      | Q4_K_M      | 2 GB            |
| 7B        | Q4_K_M      | 6 GB            |
| 7B        | Q8_0        | 10 GB           |
| 14B       | Q4_K_M      | 10 GB           |
