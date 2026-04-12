# LearnBox

A fully offline, voice-first educational assistant for students aged 8–18. Ask any school question out loud and get a clear, spoken answer — no internet, no accounts, no cloud.

Designed to run on a Raspberry Pi 5, but fully functional on Windows for development.

---

## How It Works

```
Microphone → Moonshine STT → Ollama LLM → Piper TTS → Speaker
```

Push a button (or press Enter), speak your question, and LearnBox transcribes it on-device, sends it to a local LLM, and reads the answer back aloud. Everything runs locally — no data leaves the device.

---

## Requirements

- Python 3.11
- [Ollama](https://ollama.com) running locally with the `qwen2.5:1.5b` model pulled
- A microphone and speaker connected to your device
- ~1.2 GB of disk space for the three ML models

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd LearnBox
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the Moonshine STT model (~134 MB)

```bash
python -m moonshine_voice.download --language en
```

Model is cached at `~/.cache/moonshine_voice/` (Linux) or `%LOCALAPPDATA%\moonshine_voice\` (Windows).

### 4. Download the Piper TTS voice model (~60 MB)

```bash
python3 -m piper.download_voices en_US-lessac-medium --data-dir models/
```

This creates `models/en_US-lessac-medium.onnx` and its config file.

### 5. Pull the Ollama LLM (~940 MB)

```bash
ollama pull qwen2.5:1.5b
```

Make sure the Ollama daemon is running before starting LearnBox (system tray on Windows, `ollama serve` on Linux/Pi).

---

## Running

### On Windows (development)

```bash
python main.py
```

- Press **Enter** to start recording
- Ask your question
- LearnBox plays a short audio cue, then speaks the answer
- Press **Ctrl+C** to exit

### On Raspberry Pi 5

LearnBox auto-starts on boot as a systemd service. Just power on and press the button to speak.

**Stop the service:**
```bash
sudo systemctl stop learnbox
```

**Start the service manually:**
```bash
sudo systemctl start learnbox
```

**View live logs:**
```bash
journalctl -u learnbox -f
```

**Run manually (after stopping the service):**
```bash
cd ~/LearnBox
source venv/bin/activate
python main.py
```

**Safe shutdown — always do this before unplugging:**
```bash
sudo shutdown now
```
Wait for the green activity light to stop blinking before unplugging power.

---

## Running Tests

All tests are offline-safe — no models or audio hardware required.

```bash
pytest tests/
```

---

## Project Structure

```
LearnBox/
├── learnbox/
│   ├── mic.py        # Microphone capture with energy-based VAD
│   ├── stt.py        # Moonshine speech-to-text
│   ├── llm.py        # Ollama LLM client
│   ├── tts.py        # Piper TTS synthesis + markdown stripping
│   └── audio.py      # Speaker playback
├── main.py           # Entry point — push-to-talk loop
├── models/           # Downloaded Piper voice model (git-ignored)
├── tests/            # Unit tests (pytest, fully mocked)
├── hardware.md       # Recommended Pi 5 hardware (~$110 total)
└── requirements.txt
```

---

## Configuration

No `.env` file needed. Key constants live in each module:

| Module | Constant | Default | Notes |
|--------|----------|---------|-------|
| `llm.py` | `OLLAMA_URL` | `http://localhost:11434/api/generate` | Local Ollama endpoint |
| `llm.py` | `MODEL` | `qwen2.5:1.5b` | LLM model name |
| `mic.py` | `SAMPLE_RATE` | `16000` | Hz — matches Moonshine requirement |
| `mic.py` | `DEFAULT_SILENCE_RMS` | `300` | Tune this if mic sensitivity is off |
| `tts.py` | `MODEL_PATH` | `models/en_US-lessac-medium.onnx` | Piper voice model |

To calibrate the silence threshold for your microphone:

```python
from learnbox.mic import calibrate_silence
threshold = calibrate_silence()
```

---

## Hardware (Raspberry Pi 5)

See [`hardware.md`](hardware.md) for the full parts list (~$110). Key components:

- Raspberry Pi 5 (2GB RAM)
- USB microphone
- USB speaker or 3.5mm audio output

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Audio capture & playback | Complete |
| 2 | Moonshine STT integration | Complete |
| 3 | Piper TTS + full pipeline wiring | Complete |
| 4 | Pi 5 validation & deployment scripts | Pending |

The full voice pipeline works end-to-end on Windows. Pi 5 hardware validation and setup scripts are the remaining work.
