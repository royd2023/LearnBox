#!/bin/bash
# LearnBox setup script for Raspberry Pi 5 (Raspberry Pi OS Bookworm 64-bit Lite)
# Run once on a fresh install: bash setup.sh

set -e

echo "=== LearnBox Setup ==="

# 1. System dependencies
echo "[1/7] Installing system packages..."
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git libportaudio2

# 2. Ollama
echo "[2/7] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# 3. Python virtualenv + dependencies
echo "[3/7] Creating Python virtualenv..."
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Moonshine STT model
echo "[4/7] Downloading Moonshine STT model (~134 MB)..."
python -m moonshine_voice.download --language en

# 5. Piper TTS voice model
echo "[5/7] Downloading Piper TTS voice model (~5 MB)..."
python3 -m piper.download_voices en_US-lessac-low --data-dir models/

# 6. Ollama LLM
echo "[6/7] Pulling Ollama LLM (~290 MB)..."
ollama pull qwen2.5:0.5b

# 7. Auto-start on boot
echo "[7/7] Configuring auto-start on boot..."
SERVICE_FILE=/etc/systemd/system/learnbox.service
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=LearnBox voice assistant
After=network.target sound.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable learnbox
sudo systemctl start learnbox

echo ""
echo "=== Setup complete ==="
echo "LearnBox is running. Check status with: sudo systemctl status learnbox"
echo "View logs with: journalctl -u learnbox -f"
echo "Stop with: sudo systemctl stop learnbox"
echo "SSH access remains available at any time."
