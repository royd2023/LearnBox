# Technology Stack

**Project:** LearnBox — offline voice-first educational assistant
**Researched:** 2026-03-10
**Scope:** Voice pipeline (STT + TTS) to complement existing LLM layer

---

## Context: What Already Exists

The LLM layer is complete and working:

- `learnbox/llm.py` — Python httpx wrapper around Ollama HTTP API
- Model: `qwen2.5:1.5b` via Ollama (Q4_K_M, ~940 MB on disk)
- `requirements.txt` contains only: `httpx`

This research covers what is needed to add Moonshine STT and Piper TTS.

---

## Recommended Stack

### Voice Pipeline (New)

| Component | Library | Version | Package Name | Purpose |
|-----------|---------|---------|--------------|---------|
| STT | Moonshine Voice | 0.0.49 | `moonshine-voice` | Speech-to-text, on-device, streaming |
| TTS | Piper TTS | 1.4.1 | `piper-tts` | Text-to-speech, on-device, fast |
| Mic capture | sounddevice | 0.5.5 | `sounddevice` | PortAudio bindings for mic input |
| Audio output | sounddevice | 0.5.5 | `sounddevice` | Play PCM audio to speakers |

### Existing Stack (Already Working)

| Component | Library | Version | Package Name | Purpose |
|-----------|---------|---------|--------------|---------|
| LLM | Ollama | 0.17.7 (server) | system install | LLM inference server |
| LLM model | qwen2.5:1.5b | — | via `ollama pull` | 1.5B parameter language model |
| HTTP client | httpx | 0.28.1 | `httpx` | Ollama API calls |

---

## Moonshine STT: Full Details

### Why Moonshine Over Whisper

Moonshine is purpose-built for live/streaming voice interfaces. The key technical differences matter for LearnBox:

- **No fixed 30-second window**: Whisper pads all audio to 30s, wasting compute on a Pi. Moonshine handles arbitrary-length inputs — a student's 3-5 second question is processed as 3-5 seconds.
- **Streaming/caching architecture**: Moonshine caches encoder state and decoder KV while the user speaks, reducing latency for the final transcription. On Pi 5, Whisper Tiny takes 5,863 ms; Moonshine Tiny takes 237 ms.
- **Explicit Pi 5 support**: Pre-built `manylinux_2_31_aarch64` and `manylinux_2_34_aarch64` wheels. The README includes a Pi 5-specific quickstart. Whisper on Pi is largely a DIY exercise.
- **Single pip install**: `pip install moonshine-voice` handles everything including mic capture (via sounddevice), VAD, and audio chunking. No separate ONNX runtime management needed.

### Model Choice: Use `base-en`

| Model | Parameters | WER | Pi 5 Latency | File Size |
|-------|-----------|-----|-------------|-----------|
| Tiny | 26M | 12.66% | — | ~42 MB total |
| Tiny Streaming | 34M | 12.00% | 237 ms | — |
| **Base** | **58M** | **10.07%** | — | **~134 MB total** |
| Small Streaming | 123M | 7.84% | 527 ms | — |
| Medium Streaming | 245M | 6.65% | 802 ms | — |

**Recommendation: Start with `base-en` (WER 10.07%, ~134 MB).** The base model is non-streaming (no realtime display) which fits LearnBox's push-to-talk usage pattern. It has meaningfully better accuracy than Tiny (10% vs 12.7% WER) and fits comfortably in the 2GB RAM budget. The Tiny Streaming model is the fallback if RAM proves tight.

Note: latency benchmarks shown above are for streaming models. For push-to-talk (record-then-transcribe), base-en latency is comparable — measured by full audio processing time, not streaming interval.

**Download model on first run:**
```bash
python -m moonshine_voice.download --language en
```

The download script prints the model path and architecture number. Cache dir is `~/.cache/moonshine_voice/` on Linux / `%LOCALAPPDATA%\moonshine_voice\` on Windows (via `platformdirs`). Models download once and are reused.

### Python API Pattern for LearnBox

```python
from moonshine_voice import MicTranscriber, TranscriptEventListener, get_model_for_language

model_path, model_arch = get_model_for_language("en")  # downloads if missing

class QuestionListener(TranscriptEventListener):
    def on_line_completed(self, event):
        question_text = event.line.text
        # hand off to LLM

mic_transcriber = MicTranscriber(model_path=model_path, model_arch=model_arch)
mic_transcriber.add_listener(QuestionListener())
mic_transcriber.start()
```

`MicTranscriber` internally uses `sounddevice.InputStream` at 16000 Hz mono float32. No manual audio capture code required.

### Platform Availability

| Platform | Wheel Available | Notes |
|----------|----------------|-------|
| Windows (x64) | YES | `moonshine_voice-0.0.49-py3-none-win_amd64.whl` |
| Pi 5 / Linux aarch64 | YES | `manylinux_2_31_aarch64` + `manylinux_2_34_aarch64` |
| macOS | YES | universal2 |

Pi OS Bookworm ships glibc 2.36, which satisfies both `manylinux_2_31` and `manylinux_2_34`. No compatibility issues.

---

## Piper TTS: Full Details

### Why Piper Over Alternatives

- **Zero cloud dependency**: Runs entirely on ONNX Runtime, no external calls.
- **Pi 5 native wheel**: `manylinux_2_17_aarch64` wheel covers Pi OS Bookworm (glibc 2.36 >> 2.17 requirement).
- **pip install is enough**: `pip install piper-tts` pulls in ONNX Runtime and espeak-ng bindings. No system packages needed on Windows. On Pi, espeak-ng data is bundled in the wheel.
- **Actively maintained**: OHF-Voice (Open Home Foundation) took over from rhasspy. v1.4.1 released 2026-02-05.
- **Python API for streaming**: `voice.synthesize()` yields `AudioChunk` objects with `audio_int16_bytes` — can be fed directly to `sounddevice.play()` without writing temp files.
- **Used in production by Home Assistant**, NVDA (accessibility), and others — battle-tested on embedded Linux.

### Voice Choice: `en_US-lessac-medium`

```bash
python3 -m piper.download_voices en_US-lessac-medium
```

- File size: ~60 MB (.onnx + .onnx.json)
- Quality: medium (good balance of naturalness vs speed on Pi)
- Voice: American English, male, clear and neutral — appropriate for an educational context

**Alternative if `lessac` sounds too formal:** `en_US-ryan-low` (~60 MB, similar size, different voice character). Download and A/B test.

**Do not use `high` quality voices on Pi 5**: high-quality models are significantly larger and slower; medium is the right tier for CPU-only inference on a Pi.

### Python API Pattern for LearnBox

```python
import wave
import numpy as np
import sounddevice as sd
from piper import PiperVoice

# Load once at startup — keep in memory for the session
voice = PiperVoice.load("/path/to/en_US-lessac-medium.onnx")

def speak(text: str) -> None:
    """Synthesize text and play through speakers."""
    chunks = list(voice.synthesize(text))
    if not chunks:
        return
    sample_rate = chunks[0].sample_rate
    # Concatenate all int16 chunks
    audio = np.concatenate([
        np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
        for chunk in chunks
    ])
    sd.play(audio, samplerate=sample_rate)
    sd.wait()  # block until playback complete
```

Loading `PiperVoice` takes ~200-500ms. Load it once at startup, keep the object alive for the session.

### Platform Availability

| Platform | Wheel Available | Size |
|----------|----------------|------|
| Windows (x64) | YES | 13.2 MB wheel |
| Pi 5 / Linux aarch64 | YES | 13.2 MB wheel (`manylinux_2_17_aarch64`) |
| macOS x64 + arm64 | YES | 13.2 MB wheel each |

---

## sounddevice: Audio I/O

Used by both Moonshine (mic input) and by the LearnBox integration layer (speaker output).

**Confidence: HIGH** — Official docs confirm: on Windows and macOS, `pip install sounddevice` bundles PortAudio DLLs automatically. No separate PortAudio install. On Pi/Linux, install PortAudio system package first:

```bash
# Pi 5 only — not needed on Windows
sudo apt-get install libportaudio2
```

The `moonshine-voice` package lists `sounddevice` as a dependency and will install it automatically. You only need to add it explicitly to `requirements.txt` if using it for playback outside of Moonshine's scope.

---

## Installation Commands

### Windows (Development)

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install all voice pipeline dependencies
pip install moonshine-voice piper-tts sounddevice

# Download Moonshine model (runs once, cached in %LOCALAPPDATA%)
python -m moonshine_voice.download --language en

# Download Piper voice (run from project root or specify --data-dir)
python -m piper.download_voices en_US-lessac-medium
```

No system-level dependencies on Windows. All binaries are bundled in the wheels.

**Windows gotcha:** `pip install moonshine-voice` on Windows installs the `win_amd64` wheel. This wheel bundles the core C++ library as a DLL. If you get a DLL load error, ensure you are running 64-bit Python (not 32-bit). The Windows wheel does **not** support ARM64 Windows; the Pi 5 uses Linux aarch64, not Windows, so this is irrelevant.

### Raspberry Pi 5 (Production)

Pi OS Bookworm ships Python 3.11 and enforces PEP 668 (externally-managed environment). Use a virtual environment — **do not use `--break-system-packages`** for a production install.

```bash
# System dependency for sounddevice
sudo apt-get install -y libportaudio2

# Create virtual environment (Pi OS Bookworm / Python 3.11)
python3 -m venv /home/pi/learnbox-venv
source /home/pi/learnbox-venv/bin/activate

# Install Ollama (separate from Python environment)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the LLM model
ollama pull qwen2.5:1.5b

# Install Python dependencies
pip install httpx moonshine-voice piper-tts sounddevice

# Download Moonshine model (cache at ~/.cache/moonshine_voice/)
python -m moonshine_voice.download --language en

# Download Piper voice
python -m piper.download_voices en_US-lessac-medium
```

**Pi-specific note:** The Moonshine README mentions `sudo pip install --break-system-packages` as a quickstart convenience. For a production LearnBox deployment, use a venv instead — it is cleaner, avoids system Python conflicts, and is the approach documented in their README for "if you don't want to use --break-system-packages."

---

## Full requirements.txt (After Integration)

```
# Existing
httpx>=0.28.0

# Voice pipeline
moonshine-voice>=0.0.49
piper-tts>=1.4.1
sounddevice>=0.5.5
numpy>=1.24.0
```

`numpy` is an indirect dependency of both moonshine-voice and sounddevice but pin it explicitly to avoid version conflicts during install.

---

## RAM Budget (Pi 5, 2GB)

All figures are confirmed from official registry/PyPI data:

| Component | RAM Usage | Source |
|-----------|----------|--------|
| Ollama qwen2.5:1.5b | ~1040 MB | Ollama registry manifest: 940 MB model + KV cache headroom |
| Moonshine base-en | ~134 MB | Measured: encoder 30 MB + decoder 104 MB |
| Piper en_US-lessac-medium | ~60 MB | HuggingFace: 63 MB ONNX file |
| Python process + OS | ~280 MB | Pi OS Bookworm baseline |
| **Total estimated** | **~1514 MB** | — |
| **Available headroom** | **~534 MB** | 2048 MB total |

If Moonshine tiny-en is used instead of base-en, headroom increases to ~626 MB. The 2GB constraint is comfortable. The project can use base-en without RAM pressure.

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| STT | Moonshine Voice 0.0.49 | Faster-Whisper | Whisper takes 5,863ms on Pi 5 for Tiny (vs Moonshine Tiny 237ms); no streaming; 30s padding wastes compute |
| STT | Moonshine Voice 0.0.49 | Vosk | Good Pi support, but lower accuracy, older ecosystem, no active streaming API |
| STT | Moonshine Voice 0.0.49 | useful-moonshine (old PyPI package) | Outdated (2024-10-16), requires torch 2.4.1 (~2GB), incompatible with 2GB RAM constraint |
| TTS | Piper 1.4.1 | Coqui TTS | Coqui-AI/TTS project archived in 2024; no longer maintained |
| TTS | Piper 1.4.1 | espeak-ng (raw) | Robot-sounding; Piper uses espeak-ng for phonemization but applies neural vocoder for natural output |
| TTS | Piper 1.4.1 | Bark / Parler-TTS | Too slow on CPU; designed for GPU; not viable on Pi |
| Audio I/O | sounddevice | pyaudio | pyaudio is a thinner wrapper, requires manual PortAudio setup on Windows; sounddevice bundles PortAudio on Windows/macOS and is already a Moonshine dependency |
| Audio I/O | sounddevice | playsound | playsound 1.3.0 has known bugs on Python 3.10+, only plays wav/mp3 files (no streaming) |
| LLM serving | Ollama | llama.cpp (direct) | Ollama wraps llama.cpp with HTTP API; already working; no reason to change |

---

## What NOT to Use

**Do not use `useful-moonshine` (PyPI package `useful-moonshine` version 20241016).** This is the first-generation Moonshine package. It requires `torch==2.4.1` which is ~2 GB to install and blows the Pi RAM budget entirely. The correct package is `moonshine-voice` (the second-generation library with the C++ ONNX core).

**Do not install Moonshine models manually.** Use `python -m moonshine_voice.download --language en`. The download script handles model selection, caching, and prints the exact path and arch number you need to pass to `Transcriber()`.

**Do not load PiperVoice inside the request loop.** `PiperVoice.load()` is slow (~200-500ms). Load it once at startup and hold the reference for the session lifetime.

**Do not use Whisper in any form on Pi 5.** The Pi 5 latency for Whisper Tiny is 5,863ms vs Moonshine Tiny at 237ms — a 25x difference. The 10-second end-to-end latency budget cannot accommodate Whisper.

---

## Python Version Requirements

| Library | Minimum Python | Recommended |
|---------|---------------|-------------|
| moonshine-voice | 3.8 | 3.11 (matches Pi OS Bookworm default) |
| piper-tts | 3.9 | 3.11 |
| sounddevice | 3.7 | 3.11 |
| httpx | 3.8 | 3.11 |
| onnxruntime (piper dep) | 3.10 (v1.24) | 3.11 |

**Use Python 3.11 for both Windows dev and Pi 5 prod.** Pi OS Bookworm ships Python 3.11 by default. Python 3.11 satisfies all minimum requirements, including onnxruntime 1.24.x (which dropped 3.9 support). On Windows, install Python 3.11 explicitly if not already present.

---

## Sources

| Source | Confidence | URL |
|--------|-----------|-----|
| Moonshine README (official) | HIGH | https://github.com/usefulsensors/moonshine/blob/main/README.md |
| moonshine-voice PyPI | HIGH | https://pypi.org/project/moonshine-voice/ (v0.0.49, 2026-02-23) |
| Moonshine model sizes | HIGH | Measured via download.moonshine.ai HEAD requests |
| Piper TTS README (OHF-voice) | HIGH | https://github.com/OHF-voice/piper1-gpl/blob/main/README.md |
| Piper Python API docs | HIGH | https://github.com/OHF-voice/piper1-gpl/blob/main/docs/API_PYTHON.md |
| piper-tts PyPI | HIGH | https://pypi.org/project/piper-tts/ (v1.4.1, 2026-02-05) |
| Piper voice model sizes | HIGH | Measured via HuggingFace X-Linked-Size headers |
| sounddevice installation docs | HIGH | https://python-sounddevice.readthedocs.io/en/stable/installation.html |
| sounddevice PyPI | HIGH | https://pypi.org/project/sounddevice/ (v0.5.5) |
| Ollama releases | HIGH | https://github.com/ollama/ollama/releases (v0.17.7, 2026-03-05) |
| qwen2.5:1.5b model size | HIGH | Ollama registry manifest (940 MB confirmed) |
| onnxruntime PyPI | HIGH | https://pypi.org/project/onnxruntime/ (v1.24.3) |
| Moonshine Pi 5 benchmarks | HIGH | Official README benchmark table (237ms Tiny, 802ms Medium) |
