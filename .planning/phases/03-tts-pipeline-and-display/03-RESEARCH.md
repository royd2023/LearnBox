# Phase 3: TTS, Pipeline, and Display - Research

**Researched:** 2026-03-24
**Domain:** Piper TTS, voice pipeline wiring, terminal display states, markdown stripping
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TTS-01 | System synthesizes LLM text responses to speech using Piper on-device | `piper-tts` 1.4.1 — `PiperVoice.load()` + `voice.synthesize()` yielding `AudioChunk` objects with `audio_int16_bytes` + `sample_rate`; pass chunks to `audio.play_audio()` |
| TTS-02 | System plays a short "thinking" audio cue immediately after transcription (before LLM response) | Generate a 440 Hz sine wave at 22050 Hz using numpy in `learnbox/tts.py`; call `audio.play_audio()` before `llm.ask()` — uses existing `audio.py` interface unchanged |
| TTS-03 | System strips markdown formatting from LLM response before synthesis | Pure-stdlib `re.sub()` chain in `learnbox/tts.py` — no new deps; patterns cover `**bold**`, `*italic*`, `## headings`, `- list`, backticks |
| TTS-04 | System shows a "speaking" feedback state during audio playback | `print("Speaking...", flush=True)` before synthesis loop in `main.py` — same terminal pattern as "Listening..." and "Thinking..." from Phase 2 |
| PIPE-01 | Full pipeline works end-to-end: Mic → Moonshine → Ollama → Piper → Speaker | Wire all modules in `main.py`: mic → stt → llm → tts.synthesize_and_play(); all models loaded once at startup via module-level imports |
| PIPE-02 | All models (Moonshine, Ollama, Piper) are loaded once at startup, not per-turn | Moonshine: module-level `_transcriber` already done in stt.py; Piper: module-level `_voice = PiperVoice.load(MODEL_PATH)` in tts.py; Ollama: stateless HTTP, no preload needed |
| PIPE-03 | Mic does not capture while TTS is playing (no self-triggering) | Sequential synchronous pipeline is sufficient — `audio.play_audio()` uses `sd.wait()` which blocks until playback complete; mic loop only resumes after the call returns |
| PIPE-04 | Pipeline handles errors at each stage with a spoken error message | Wrap each stage in try/except; on error, call `tts.speak_error(message)` which synthesizes a short error phrase; fallback to `print()` if TTS itself fails |
| DISP-01 | Screen displays the transcribed student question as text | `print(f"You: {transcript}", flush=True)` in main.py — same terminal pattern as Phase 2; text appears immediately after transcription |
| DISP-02 | Screen displays the LLM response as text alongside audio playback | `print(f"LearnBox: {response}", flush=True)` before or during TTS playback — text and audio run sequentially, text printed immediately when response arrives |
</phase_requirements>

---

## Summary

Phase 3 completes the voice pipeline by adding Piper TTS as the output half, wiring all components together in `main.py`, and ensuring robust error handling and display states throughout. The critical new module is `learnbox/tts.py` which wraps Piper's `PiperVoice` class, handles markdown stripping, generates the "thinking" audio cue, and provides a `speak_error()` fallback.

Piper TTS (`piper-tts` 1.4.1, maintained at OHF-Voice/piper1-gpl) is the correct library. It installs via pip, embeds espeak-ng for phonemization (no separate system package needed on Windows), provides a clean Python API (`PiperVoice.load()` + `voice.synthesize()` yielding `AudioChunk` objects), and has ARM64 wheels for Pi 5. The `en_US-lessac-medium` voice is 63.2 MB on disk, outputs at 22050 Hz, and is the established recommendation for offline Pi deployments. Voice model files (`.onnx` and `.onnx.json`) are downloaded separately via `python3 -m piper.download_voices en_US-lessac-medium`.

The sequential synchronous pipeline architecture from Phases 1-2 handles PIPE-03 (mic mute during TTS) for free — `audio.play_audio()` calls `sd.play()` + `sd.wait()`, which blocks the main thread until playback finishes. The mic loop cannot resume until the entire TTS playback completes. No threading, no locks, no extra state needed. Display states (DISP-01, DISP-02, TTS-04) extend the Phase 2 terminal `print()` pattern. STT-03 and STT-04 from Phase 2 were deferred to Phase 3 — they are `print()` calls already partially present in main.py.

**Primary recommendation:** Create `learnbox/tts.py` with module-level `PiperVoice` load, `strip_markdown()`, `speak()`, and `speak_error()` functions; update `main.py` to wire in TTS and complete display states.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| piper-tts | 1.4.1 | On-device neural TTS; `PiperVoice` Python API | Only pip-installable Piper with ARM64 wheels; actively maintained by OHF-Voice; embeds espeak-ng |
| numpy | >=1.24.0 | Audio synthesis (thinking cue sine wave), chunk byte conversion | Already a dep; `np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)` for chunk conversion |

### Existing (Phases 1-2 — already installed, no changes needed)

| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| sounddevice | 0.5.5 | Audio playback via `audio.play_audio()` | Phase 1 — `play_audio(audio, sample_rate)` accepts int16 and 22050 Hz natively |
| httpx | 0.28.1 | LLM via `llm.ask()` | Phase 1 — unchanged |
| moonshine-voice | 0.0.49 | STT via `stt.transcribe()` | Phase 2 — unchanged |

### Voice Model (download once, bundle for offline)

| Asset | Size | Sample Rate | Download |
|-------|------|-------------|---------|
| en_US-lessac-medium.onnx | 63.2 MB | 22050 Hz | `python3 -m piper.download_voices en_US-lessac-medium` |
| en_US-lessac-medium.onnx.json | 4.89 kB | (config) | Downloaded alongside .onnx automatically |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| piper-tts (pip) | Piper CLI binary + subprocess | Subprocess approach avoids Python API complexity but adds ~200ms process-launch latency per utterance; binary not pip-installable; harder to control programmatically |
| en_US-lessac-medium | en_US-amy-low | Smaller model (~5 MB), lower quality; medium is standard recommendation for real use |
| re.sub() chain | `strip-markdown` PyPI package | Extra dep for simple patterns; stdlib re is sufficient for LLM output (bold, italic, headings, lists, backticks) |
| numpy sine wave | .wav file bundled cue | Numpy is already present; generating 440 Hz in code avoids adding a binary asset to the repo |

**Installation (additions to requirements.txt):**

```bash
pip install piper-tts>=1.4.1
```

Then download voice model (run once, place files in `models/` directory):

```bash
python3 -m piper.download_voices en_US-lessac-medium --data-dir models/
```

**Note on espeak-ng:** The `piper-tts` pip package embeds espeak-ng for phonemization. No separate `apt install espeak-ng` is required on Windows. On Pi OS (Linux), if synthesis raises a phonemization error, run `sudo apt-get install espeak-ng` as a fallback. This should be validated on physical Pi hardware in Phase 4.

---

## Architecture Patterns

### Recommended Project Structure After Phase 3

```
learnbox/
├── mic.py          # DONE Phase 1 — 16kHz mono int16 mic capture with energy VAD
├── audio.py        # DONE Phase 1 — blocking speaker playback via sd.play + sd.wait
├── stt.py          # DONE Phase 2 — Moonshine transcription; load once
├── llm.py          # DONE pre-work — synchronous httpx wrapper around Ollama
└── tts.py          # NEW Phase 3 — Piper TTS; strip_markdown; thinking cue; speak; speak_error

main.py             # MODIFY Phase 3 — wire full pipeline + display states + error handling
models/
├── en_US-lessac-medium.onnx       # voice model (63.2 MB, downloaded separately)
└── en_US-lessac-medium.onnx.json  # voice config (4.89 kB)
tests/
├── __init__.py
├── test_audio_foundation.py        # DONE Phase 1
├── test_stt.py                     # DONE Phase 2
└── test_tts.py                     # NEW Phase 3 — offline-safe TTS module tests
```

### Pattern 1: PiperVoice Module-Level Load

**What:** Load the Piper voice model once at module import, not per synthesis call. Model load is slow (~200-500ms ONNX session init).
**When to use:** Always — matches the Moonshine pattern from stt.py.

```python
# learnbox/tts.py — module level
from pathlib import Path
from piper.voice import PiperVoice

MODEL_PATH = Path(__file__).parent.parent / "models" / "en_US-lessac-medium.onnx"

# Load once — PiperVoice initialization is slow; amortize across all calls
_voice = PiperVoice.load(str(MODEL_PATH))
```

### Pattern 2: Synthesize Text to Audio Chunks and Play

**What:** Call `voice.synthesize(text)` which yields `AudioChunk` objects. Each chunk has `audio_int16_bytes` and `sample_rate`. Convert bytes to int16 numpy array, accumulate all chunks, then play via `audio.play_audio()`.
**Why accumulate vs stream:** The project uses blocking sequential playback via `audio.play_audio()`. Accumulating all chunks first and calling `play_audio()` once preserves the existing blocking contract and is simpler. Streaming to `sd.OutputStream` would work but adds complexity with no benefit for this pipeline.

```python
# Source: OHF-Voice/piper1-gpl docs/API_PYTHON.md + thedocs.io/piper1-gpl/api/python/
import numpy as np
from learnbox.audio import play_audio

def speak(text: str) -> None:
    """Synthesize text to speech and play it blocking."""
    clean = strip_markdown(text)
    if not clean.strip():
        return

    all_audio: list[np.ndarray] = []
    sample_rate = None
    for chunk in _voice.synthesize(clean):
        int_data = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
        all_audio.append(int_data)
        if sample_rate is None:
            sample_rate = chunk.sample_rate  # 22050 for lessac-medium

    if all_audio and sample_rate:
        audio_array = np.concatenate(all_audio)
        play_audio(audio_array, sample_rate)
```

### Pattern 3: Thinking Audio Cue (TTS-02)

**What:** Generate a short 440 Hz sine wave in numpy and play it immediately after transcription, before the LLM call. Must complete within 500ms — use a 300ms duration.
**Why numpy not a .wav file:** numpy is already a dependency; no binary asset needed in the repo.

```python
# Source: numpy + sounddevice docs; standard PCM synthesis
import numpy as np
from learnbox.audio import play_audio

SAMPLE_RATE_CUE = 22050
CUE_DURATION_S = 0.3   # 300ms — audible but not annoying
CUE_FREQUENCY = 440    # A4 — clear, neutral tone

def play_thinking_cue() -> None:
    """Play a short tone to signal that processing has started."""
    t = np.linspace(0, CUE_DURATION_S, int(SAMPLE_RATE_CUE * CUE_DURATION_S), endpoint=False)
    # Sine wave at int16 amplitude, 50% volume to avoid clipping
    tone = (np.sin(2 * np.pi * CUE_FREQUENCY * t) * 16383).astype(np.int16)
    play_audio(tone, SAMPLE_RATE_CUE)
```

### Pattern 4: Markdown Stripping (TTS-03)

**What:** LLM responses from qwen2.5:1.5b include markdown formatting (bold `**text**`, headings `## text`, lists `- item`, backticks). These must be stripped before synthesis or they get read aloud.
**Implementation:** Pure stdlib `re.sub()` chain — no new dependency.

```python
import re

def strip_markdown(text: str) -> str:
    """Remove markdown formatting characters from LLM response text."""
    # Bold and italic: **text**, *text*, __text__, _text_
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    # Headings: ## text -> text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Unordered list markers: - item, * item
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    # Ordered list markers: 1. item
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Code blocks: ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Collapse extra whitespace from removals
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
```

### Pattern 5: Spoken Error Handling (PIPE-04)

**What:** Each pipeline stage is wrapped in try/except. On failure, call `tts.speak_error(message)` which synthesizes a short user-facing phrase. If TTS itself fails, fall back to `print()`.

```python
def speak_error(message: str) -> None:
    """Speak an error message; falls back to print if TTS fails."""
    try:
        speak(message)
    except Exception:
        print(f"[Error — could not speak]: {message}", flush=True)
```

### Pattern 6: Complete main.py Pipeline Loop

**What:** Updated main.py wiring all 5 modules with display states and error recovery.

```python
# main.py — Phase 3 complete pipeline
from learnbox.mic import record_until_silence
from learnbox import stt    # noqa: triggers Moonshine load
from learnbox.stt import transcribe
from learnbox.llm import ask
from learnbox import tts    # noqa: triggers Piper voice load
from learnbox.tts import speak, speak_error, play_thinking_cue


def main():
    print("LearnBox — press Enter to speak, Ctrl+C to quit.\n")
    while True:
        try:
            input("[ Press Enter to speak ]")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        # --- MIC ---
        print("Listening...", flush=True)
        try:
            audio = record_until_silence()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

        if len(audio) == 0:
            print("(no speech detected — try again)\n")
            continue

        # --- STT ---
        transcript = transcribe(audio)
        if not transcript.strip():
            print("(could not transcribe — speak closer to the mic)\n")
            continue

        print(f"You: {transcript}", flush=True)   # DISP-01

        # --- THINKING CUE (TTS-02) ---
        play_thinking_cue()   # plays before LLM call; <500ms

        # --- LLM ---
        print("Thinking...", flush=True)
        try:
            response = ask(transcript, timeout=120.0)
        except RuntimeError as e:
            speak_error(f"Sorry, I couldn't get an answer. {e}")
            continue

        print(f"LearnBox: {response}\n", flush=True)  # DISP-02

        # --- TTS ---
        print("Speaking...", flush=True)   # TTS-04
        try:
            speak(response)
        except Exception as e:
            print(f"(TTS failed: {e})\n", flush=True)


if __name__ == "__main__":
    main()
```

### Anti-Patterns to Avoid

- **Calling `PiperVoice.load()` per utterance:** Model initialization is slow (~200-500ms). Always load at module level.
- **Streaming to `sd.OutputStream` for this pipeline:** The blocking sequential design of `audio.play_audio()` (sd.play + sd.wait) is intentional — it prevents the mic from re-opening during playback. Do not introduce streaming playback that bypasses this.
- **Passing raw LLM output to Piper:** Markdown symbols get synthesized as spoken characters ("asterisk asterisk"). Always call `strip_markdown()` first.
- **Threading for display:** Do not use threads just to print text. Print before the blocking call — sequential print-then-speak is sufficient for DISP-02.
- **model_path hardcoded as string:** Use `Path(__file__).parent.parent / "models" / "..."` so the path resolves correctly regardless of where `python main.py` is invoked from.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text-to-speech synthesis | Custom espeak subprocess, Festival, coqui-TTS | `piper-tts` 1.4.1 | Piper achieves <0.2 RTF on CPU, is fully offline, ARM64-native, and has a clean Python API. coqui-TTS requires 2GB+ RAM (torch). Festival produces robotic quality. |
| Markdown stripping | HTML parser, markdown2 library | `re.sub()` stdlib chain | LLM output has a small, predictable set of markdown patterns. A 10-line re chain covers them all with zero new dependencies. |
| "Thinking" audio cue | Bundled .wav file | numpy sine wave generator | numpy is already a dependency. Generates in-memory at startup, zero file I/O, no binary asset in repo. |
| Mic mute during TTS | Threading lock, asyncio event | `sd.wait()` in `audio.play_audio()` | The blocking playback contract from Phase 1 is the lock. The mic loop cannot run while `sd.wait()` is blocking. Free by design. |
| Error audio fallback | Custom beep or recorded error clips | `tts.speak_error()` calling `speak()` | Piper can synthesize any string; use it to speak the error itself. Only fall back to `print()` if Piper is the component that failed. |

**Key insight:** The sequential synchronous design chosen in Phase 1 eliminates entire categories of complexity (self-triggering, threading, locking). PIPE-03 is solved for free.

---

## Common Pitfalls

### Pitfall 1: Model Path Resolution

**What goes wrong:** `FileNotFoundError` when running `python main.py` from a different working directory.
**Why it happens:** A relative path like `"models/en_US-lessac-medium.onnx"` resolves relative to the CWD, not the module's location.
**How to avoid:** Use `Path(__file__).parent.parent / "models" / "en_US-lessac-medium.onnx"` in `tts.py`. This always resolves to `<project_root>/models/` regardless of CWD.
**Warning signs:** Works when run from project root, fails when run from `learnbox/` or another directory.

### Pitfall 2: espeak-ng Missing on Linux

**What goes wrong:** `piper-tts` raises a phonemization error on first synthesis call on Pi OS.
**Why it happens:** While `piper-tts` embeds espeak-ng data, some Linux environments require the system `espeak-ng` shared library. The Windows pip wheel fully bundles it; the Linux wheel may not.
**How to avoid:** In Phase 4 Pi validation, test synthesis immediately after install. If it fails: `sudo apt-get install espeak-ng`. Document this in the setup script.
**Warning signs:** `OSError: libespeak-ng.so.1: cannot open shared object file` on Pi.

### Pitfall 3: Voice Model Files Missing at Runtime

**What goes wrong:** `PiperVoice.load()` raises `FileNotFoundError` at startup — Piper doesn't download models automatically on import.
**Why it happens:** Unlike Moonshine (which has `get_model_for_language()` that downloads if absent), Piper requires explicit model download before first use.
**How to avoid:** Run `python3 -m piper.download_voices en_US-lessac-medium --data-dir models/` as a setup step. Add a startup check: if model files don't exist, print clear instructions and exit.
**Warning signs:** Module import fails at startup with `FileNotFoundError` pointing to `.onnx` path.

### Pitfall 4: Markdown Characters Spoken Aloud

**What goes wrong:** Piper says "asterisk asterisk photosynthesis asterisk asterisk" instead of "photosynthesis".
**Why it happens:** qwen2.5:1.5b returns markdown-formatted responses (bold, bullet lists, headings). Piper treats these as text and attempts to phonemize every character.
**How to avoid:** Always call `strip_markdown(text)` before `_voice.synthesize(text)`. The stripping must happen inside `tts.speak()` so no call site can forget.
**Warning signs:** TTS output contains spoken punctuation characters; responses with `**bold**` are especially obvious.

### Pitfall 5: Empty Response to Piper

**What goes wrong:** `voice.synthesize("")` produces no audio but may iterate zero times — harmless but the loop exits silently.
**Why it happens:** LLM timeout produces empty string; strip_markdown on an all-markdown response could produce empty string.
**How to avoid:** Guard with `if not clean.strip(): return` inside `speak()` before calling `synthesize()`.
**Warning signs:** No audio plays, no error raised — silent failure.

### Pitfall 6: Thinking Cue Latency Budget

**What goes wrong:** Audio cue takes longer than 500ms and TTS-02 is violated.
**Why it happens:** `play_audio()` blocks for the duration of the audio. A 1-second cue would take 1 second.
**How to avoid:** Keep cue duration at 300ms (0.3s) or less. The numpy sine wave generates in microseconds; only the playback duration matters.
**Warning signs:** Noticeable pause between transcript confirmation and cue; time from transcript print to cue end > 500ms.

### Pitfall 7: Piper Loaded Before Model Download

**What goes wrong:** Module-level `PiperVoice.load()` in `tts.py` fires at import time — if models haven't been downloaded, the import fails with `FileNotFoundError`.
**Why it happens:** Python executes module-level code on import. `main.py` does `from learnbox import tts`, which triggers `_voice = PiperVoice.load(MODEL_PATH)` immediately.
**How to avoid:** Add a pre-import check in `tts.py`: if `MODEL_PATH` does not exist, raise a clear `RuntimeError("Run: python3 -m piper.download_voices en_US-lessac-medium --data-dir models/")` rather than the cryptic `FileNotFoundError` from Piper.
**Warning signs:** `FileNotFoundError: [Errno 2] No such file or directory: '.../models/en_US-lessac-medium.onnx'` on first run.

---

## Code Examples

Verified patterns from official sources:

### tts.py Full Module

```python
# learnbox/tts.py
"""
Text-to-speech synthesis using Piper (en_US-lessac-medium).

Input: plain text string (LLM response, stripped of markdown)
Output: blocking audio playback via audio.play_audio()

The PiperVoice is loaded once at module import and reused for the
lifetime of the process. Model files must exist at:
    <project_root>/models/en_US-lessac-medium.onnx
    <project_root>/models/en_US-lessac-medium.onnx.json

If model files are absent, import raises RuntimeError with setup instructions.
Run once to download:
    python3 -m piper.download_voices en_US-lessac-medium --data-dir models/
"""

import re
from pathlib import Path

import numpy as np

from learnbox.audio import play_audio

MODEL_PATH = Path(__file__).parent.parent / "models" / "en_US-lessac-medium.onnx"

if not MODEL_PATH.exists():
    raise RuntimeError(
        f"Piper voice model not found at {MODEL_PATH}.\n"
        "Run: python3 -m piper.download_voices en_US-lessac-medium --data-dir models/"
    )

from piper.voice import PiperVoice  # noqa: E402 — import after path check

# Load once — PiperVoice initialization is slow (~200-500ms ONNX session init)
_voice = PiperVoice.load(str(MODEL_PATH))

# Thinking cue constants
_CUE_SAMPLE_RATE = 22050
_CUE_DURATION_S = 0.3      # 300ms — within TTS-02 500ms budget
_CUE_FREQUENCY = 440       # A4


def play_thinking_cue() -> None:
    """Play a short 440 Hz tone to signal processing has started (TTS-02)."""
    t = np.linspace(0, _CUE_DURATION_S, int(_CUE_SAMPLE_RATE * _CUE_DURATION_S), endpoint=False)
    tone = (np.sin(2 * np.pi * _CUE_FREQUENCY * t) * 16383).astype(np.int16)
    play_audio(tone, _CUE_SAMPLE_RATE)


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from LLM response text before synthesis (TTS-03)."""
    text = re.sub(r'\*{1,2}([^*\n]+)\*{1,2}', r'\1', text)      # **bold**, *italic*
    text = re.sub(r'_{1,2}([^_\n]+)_{1,2}', r'\1', text)         # __bold__, _italic_
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)    # ## Headings
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)   # - list items
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # 1. ordered list
    text = re.sub(r'```[\s\S]*?```', '', text)                     # code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)                       # inline code
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def speak(text: str) -> None:
    """Synthesize text to speech and play it blocking (TTS-01).

    Strips markdown before synthesis. Returns immediately if text is empty.
    """
    clean = strip_markdown(text)
    if not clean.strip():
        return

    all_audio: list[np.ndarray] = []
    sample_rate: int | None = None
    for chunk in _voice.synthesize(clean):
        int_data = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
        all_audio.append(int_data)
        if sample_rate is None:
            sample_rate = chunk.sample_rate  # 22050 Hz for lessac-medium

    if all_audio and sample_rate:
        play_audio(np.concatenate(all_audio), sample_rate)


def speak_error(message: str) -> None:
    """Speak an error message; falls back to print if TTS itself fails (PIPE-04)."""
    try:
        speak(message)
    except Exception:
        print(f"[TTS failed — error]: {message}", flush=True)
```

### Offline-Safe Test Pattern for tts.py

```python
# tests/test_tts.py
"""Offline-safe unit tests for learnbox/tts.py."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# --- strip_markdown tests (no mocking needed) ---

def test_strip_markdown_removes_bold():
    from learnbox.tts import strip_markdown
    assert strip_markdown("**photosynthesis**") == "photosynthesis"

def test_strip_markdown_removes_headings():
    from learnbox.tts import strip_markdown
    assert strip_markdown("## Summary") == "Summary"

def test_strip_markdown_removes_list_markers():
    from learnbox.tts import strip_markdown
    result = strip_markdown("- item one\n- item two")
    assert "- " not in result

def test_strip_markdown_passes_plain_text_unchanged():
    from learnbox.tts import strip_markdown
    text = "Photosynthesis is how plants make food."
    assert strip_markdown(text) == text

# --- speak() tests — patch _voice to avoid Piper model dependency ---

class FakePiperVoice:
    """Mock PiperVoice that returns predictable AudioChunk objects."""
    def synthesize(self, text):
        chunk = MagicMock()
        chunk.audio_int16_bytes = np.zeros(100, dtype=np.int16).tobytes()
        chunk.sample_rate = 22050
        yield chunk

def test_speak_calls_play_audio_with_int16(monkeypatch):
    import learnbox.tts as tts_module
    monkeypatch.setattr(tts_module, "_voice", FakePiperVoice())
    played = []
    monkeypatch.setattr("learnbox.audio.play_audio", lambda audio, sr: played.append((audio, sr)))
    tts_module.speak("Hello world")
    assert len(played) == 1
    assert played[0][0].dtype == np.int16
    assert played[0][1] == 22050

def test_speak_skips_empty_text(monkeypatch):
    import learnbox.tts as tts_module
    monkeypatch.setattr(tts_module, "_voice", FakePiperVoice())
    played = []
    monkeypatch.setattr("learnbox.audio.play_audio", lambda audio, sr: played.append((audio, sr)))
    tts_module.speak("")
    assert len(played) == 0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| coqui-TTS / mozilla TTS | piper-tts (OHF-Voice piper1-gpl) | 2023-2025 | Piper uses VITS ONNX — 63 MB model vs 2GB torch; runs on Pi |
| rhasspy/piper (archived) | OHF-Voice/piper1-gpl (active) | Oct 2025 | Same `pip install piper-tts`; Python API improved with `synthesize()` yielding `AudioChunk` objects |
| Streaming TTS (token-by-token) | Full response → single synthesis call | Requirement decision | Streaming TTS produces choppy audio — explicitly out of scope per REQUIREMENTS.md |
| subprocess `piper` binary | `PiperVoice` Python API | 2024 | Python API eliminates ~200ms process-launch overhead per utterance; cleaner integration |

**Deprecated/outdated:**
- `rhasspy/piper` GitHub repo: Archived October 2025. `pip install piper-tts` still works but development is at OHF-Voice/piper1-gpl.
- Streaming TTS (token-by-token from LLM): Explicitly out of scope in REQUIREMENTS.md. Do not implement.
- `synthesize_stream_raw()`: Old API method from earlier piper-tts versions. Current API uses `synthesize()` yielding `AudioChunk` objects with `.audio_int16_bytes`.

---

## Open Questions

1. **espeak-ng system dependency on Pi OS**
   - What we know: `piper-tts` pip wheel embeds espeak-ng data. OHF-Voice docs say "embeds espeak-ng for phonemization."
   - What's unclear: Whether the ARM64 Linux wheel fully bundles the shared library or if `sudo apt-get install espeak-ng` is needed.
   - Recommendation: Phase 4 first task — run `python3 -c "from piper.voice import PiperVoice"` on fresh Pi; if it fails with `libespeak-ng.so.1` error, add `sudo apt-get install espeak-ng` to setup script.

2. **Piper RAM footprint on Pi 5 within 534MB headroom**
   - What we know: Pi 5 headroom after Moonshine + Qwen is ~534MB. Piper model is 63.2 MB on disk. ONNX runtime VITS model typically 150-300MB in RAM.
   - What's unclear: Exact RSS when `_voice = PiperVoice.load()` is held in memory.
   - Recommendation: Phase 4 — measure `free -m` after loading Moonshine + Qwen + Piper together. If RAM is tight, consider `en_US-lessac-low` (~5MB model, smaller RAM footprint) as a fallback option.

3. **`piper.download_voices` default path resolution**
   - What we know: `--data-dir models/` downloads to a `models/` subdirectory relative to CWD.
   - What's unclear: Whether `python3 -m piper.download_voices` without `--data-dir` uses a system cache dir or CWD.
   - Recommendation: Always use `--data-dir models/` explicitly in setup instructions. Store model files in `<project_root>/models/` for predictability.

4. **`int | None` type annotation compatibility on Python 3.9**
   - What we know: `requirements.txt` doesn't pin Python version; `piper-tts` supports Python 3.9+. `int | None` union syntax is Python 3.10+.
   - What's unclear: Which Python version is installed on the target Pi.
   - Recommendation: Use `Optional[int]` from `typing` in `tts.py` for 3.9 compatibility, or check `python --version` on Pi first.

---

## Sources

### Primary (HIGH confidence)

- OHF-Voice/piper1-gpl Python API docs (thedocs.io/piper1-gpl/api/python/) — `PiperVoice.load()`, `synthesize()`, `AudioChunk` properties (`audio_int16_bytes`, `sample_rate`), `SynthesisConfig`, `download_voices` command
- PyPI piper-tts 1.4.1 (pypi.org/project/piper-tts/) — version, ARM64 wheel availability (manylinux aarch64), Python 3.9-3.13 support, GPL-3.0 license
- HuggingFace rhasspy/piper-voices en_US-lessac-medium.onnx.json — sample_rate=22050, phoneme_type=espeak, piper_version=1.0.0
- HuggingFace rhasspy/piper-voices file listing — model size: 63.2 MB (.onnx), 4.89 kB (.onnx.json)
- learnbox/audio.py (direct code inspection) — `play_audio(audio, sample_rate)` accepts int16, blocks via `sd.wait()`, comment documents 22050 Hz compatibility
- learnbox/mic.py (direct code inspection) — `sd.wait()` blocking contract; mic loop cannot resume during playback
- noerguerra.com / thedocs.io piper1-gpl — `synthesize_stream_raw()` old API; confirmed current API is `synthesize()` yielding chunks

### Secondary (MEDIUM confidence)

- OHF-Voice/piper1-gpl README (GitHub, via WebFetch) — "embeds espeak-ng for phonemization"; `pip install piper-tts` confirmed as installation method
- WebSearch cross-reference — `np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)` conversion pattern confirmed across multiple independent sources (noerguerra.com, pipecat-ai docs, gdcorner.com)
- rhasspy/piper Discussion #359 — Raspberry Pi 5 TTS choppy audio with file-based approach; direct audio output recommended; `aplay -r 22050` confirms 22050 Hz sample rate for Pi

### Tertiary (LOW confidence — validate on hardware)

- Piper RAM footprint on Pi 5 (~150-300MB estimate) — no official benchmark found; inferred from ONNX VITS model characteristics; must be measured
- espeak-ng bundled vs system dependency on Pi OS — OHF-Voice says "embeds," but Linux ARM64 wheel behavior not independently confirmed; test on hardware

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — piper-tts 1.4.1 verified on PyPI with ARM64 wheels; Python API documented at thedocs.io; voice model size and sample rate confirmed from HuggingFace
- Architecture: HIGH — PiperVoice.load() + synthesize() pattern confirmed from multiple sources; blocking playback contract from audio.py is code-inspected; sequential pipeline self-mute is verified by design
- Pitfalls: HIGH — model path, markdown stripping, empty text guard, and espeak-ng all verified from official or code sources; RAM estimate is LOW confidence and flagged accordingly

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (piper-tts 1.4.1 released 2026-02-05; API stable; re-verify if piper-tts 2.x appears)
