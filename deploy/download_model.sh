#!/usr/bin/env bash
# Download Qwen 2.5 7B Instruct GGUF model
# Usage: ./download_model.sh [q2k|q3km|q4km|q5km]

set -euo pipefail

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MODEL_DIR="/opt/qwen-assistant/models"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

# Default to Q3_K_M (good balance of quality and size)
QUANT="${1:-q3km}"

echo -e "${BLUE}=== Qwen Model Downloader ===${NC}"
echo ""

case "$QUANT" in
    q2k)
        echo -e "${GREEN}Downloading Q2_K (3.02 GB - Fastest, lower quality)${NC}"
        URL="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q2_k.gguf"
        wget -O qwen.gguf "$URL"
        ;;
    q3km)
        echo -e "${GREEN}Downloading Q3_K_M (3.81 GB - Good quality, recommended)${NC}"
        URL="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q3_k_m.gguf"
        wget -O qwen.gguf "$URL"
        ;;
    q4km)
        echo -e "${GREEN}Downloading Q4_K_M (4.68 GB - Better quality, 2 parts)${NC}"
        wget "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
        wget "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf"
        echo -e "${YELLOW}Note: Q4_K_M is split into 2 files. Update .env to use: qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf${NC}"
        ;;
    q5km)
        echo -e "${GREEN}Downloading Q5_K_M (5.44 GB - High quality, 2 parts)${NC}"
        wget "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf"
        wget "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q5_k_m-00002-of-00002.gguf"
        echo -e "${YELLOW}Note: Q5_K_M is split into 2 files. Update .env to use: qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf${NC}"
        ;;
    *)
        echo -e "${YELLOW}Usage: $0 [q2k|q3km|q4km|q5km]${NC}"
        echo ""
        echo "Available quantizations:"
        echo "  q2k  - Q2_K   (3.02 GB) - Fastest, lower quality"
        echo "  q3km - Q3_K_M (3.81 GB) - Good quality (default, recommended)"
        echo "  q4km - Q4_K_M (4.68 GB) - Better quality"
        echo "  q5km - Q5_K_M (5.44 GB) - High quality"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓ Download complete!${NC}"
echo ""
echo "Model location: $MODEL_DIR"
ls -lh "$MODEL_DIR"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Verify .env has correct MODEL_PATH"
echo "2. Continue with deployment: cd /opt/qwen-assistant && ./deploy/setup_vps_root.sh"
