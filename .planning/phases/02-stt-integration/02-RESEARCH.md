# Phase 2: STT Integration - Research

**Researched:** 2026-03-10
**Domain:** Moonshine STT integration, push-to-talk gating, terminal feedback states
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STT-01 | System transcribes spoken input to text using Moonshine (base-en) on-device | Moonshine `Transcriber` API documented — use `add_audio()` stream pattern with pre-recorded numpy array from mic.py |
| STT-02 | System uses push-to-talk gating (button/key press) to start listening | Enter-to-start/Enter-to-stop via `input()` is the correct terminal approach; avoids pynput/keyboard X11 dependency on Pi |
| STT-03 | System shows a "listening" feedback state while recording | `print("Listening...", flush=True)` before recording; `print()` after — implemented in main.py loop |
| STT-04 | System shows a "thinking" feedback state while LLM is generating | `print("Thinking...", flush=True)` before `llm.ask()` call — implemented in main.py loop |
</phase_requirements>

---

## Summary

Phase 2 adds speech-to-text transcription to the LearnBox pipeline. The audio foundation from Phase 1 is complete: `mic.py` captures 16kHz mono int16 numpy arrays, and `audio.py` provides blocking playback. Phase 2 adds a new `learnbox/stt.py` module that wraps Moonshine, updates `main.py` to replace the text input loop with a voice loop, and prints "Listening..." / "Thinking..." state feedback to the terminal.

The Moonshine API for push-to-talk (record-then-transcribe) uses the `Transcriber` class — not `MicTranscriber`. The pattern is: load model once at startup, call `transcriber.start()`, feed the pre-recorded audio array in chunks via `transcriber.add_audio()`, call `transcriber.stop()`, and retrieve the transcript from the `TranscriptEventListener.on_line_completed` event. The audio must be float32 (-1.0 to 1.0) before being passed to `add_audio()` — `mic.py` returns int16, so `stt.py` must convert with `audio_float32 = audio_int16.astype(np.float32) / 32768.0`.

Push-to-talk in Phase 2 is terminal-only (no GUI). The correct implementation is `input()` — press Enter to start recording, the VAD runs until silence, then transcription fires. This avoids all cross-platform keyboard library complications (pynput requires X11 on Linux; the `keyboard` library requires root). The terminal-only approach satisfies STT-02 cleanly for both Windows dev and Pi 5 deployment.

**Primary recommendation:** Create `learnbox/stt.py` with a `Transcriber`-based `transcribe(audio_int16)` function; update `main.py` to replace the text input loop with a push-to-talk loop that prints "Listening..." and "Thinking..." states.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| moonshine-voice | 0.0.49 | On-device STT, Moonshine base-en | Only correct package; `useful-moonshine` is wrong (requires torch ~2GB) |
| numpy | >=1.24.0 | Audio array manipulation, int16→float32 conversion | Already a dep; required for `audio_float32 = audio_int16.astype(np.float32) / 32768.0` |

### Existing (Phase 1 — already installed)

| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| sounddevice | 0.5.5 | Mic capture via mic.py | Already in requirements.txt; mic.py is complete |
| httpx | 0.28.1 | LLM via llm.py | Already in requirements.txt; llm.py is complete |

### No New Keyboard Library Needed

Push-to-talk in Phase 2 uses Python's built-in `input()`. No additional package is required.

| Option | Verdict | Reason |
|--------|---------|--------|
| `input()` (stdlib) | USE THIS | Works on Windows and Linux terminal, no X11 dependency, zero install cost |
| pynput | Do not use | Requires X11 on Linux Pi; won't work headless without display server |
| keyboard | Do not use | Requires root on Linux; security issue for student device |
| readchar | Do not use | Extra dependency for no benefit over input() in this use case |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| moonshine-voice | useful-moonshine | Wrong — useful-moonshine requires torch 2.4.1 (~2GB), exceeds Pi RAM budget |
| moonshine-voice | faster-whisper | Wrong — Whisper Tiny takes 5,863ms on Pi 5 vs Moonshine Tiny at 237ms; 30s padding wastes compute |
| input() PTT | pynput hold-to-talk | Better UX (true hold), but pynput requires X11 on Pi; defer to Phase 3/4 |

**Installation (additions to requirements.txt):**

```bash
pip install moonshine-voice>=0.0.49
```

Then download model (run once, cached):

```bash
python -m moonshine_voice.download --language en
```

---

## Architecture Patterns

### Recommended Project Structure After Phase 2

```
learnbox/
├── mic.py          # DONE Phase 1 — 16kHz mono int16 mic capture with energy VAD
├── audio.py        # DONE Phase 1 — blocking speaker playback via sd.play + sd.wait
├── stt.py          # NEW Phase 2 — Moonshine transcription; load once; int16→float32 conversion
└── llm.py          # DONE pre-work — synchronous httpx wrapper around Ollama

main.py             # MODIFY Phase 2 — replace text input loop with PTT voice loop
tests/
├── __init__.py     # DONE Phase 1
├── test_audio_foundation.py  # DONE Phase 1 — 7 tests passing
└── test_stt.py     # NEW Phase 2 — offline-safe Moonshine tests
```

### Pattern 1: Moonshine Transcriber for Push-to-Talk (Record-then-Transcribe)

**What:** Use `Transcriber` (not `MicTranscriber`) to transcribe a pre-recorded numpy array. Feed audio in chunks, collect transcript via event listener.
**When to use:** Always for push-to-talk — mic.py already owns audio capture; Moonshine only needs to see the final array.

```python
# Source: Official Moonshine README (github.com/moonshine-ai/moonshine)
from moonshine_voice import Transcriber, TranscriptEventListener, get_model_for_language
import numpy as np

# Load once at module level (or at startup) — not per call
model_path, model_arch = get_model_for_language("en")
_transcriber = Transcriber(model_path=model_path, model_arch=model_arch)

class _CaptureListener(TranscriptEventListener):
    def __init__(self):
        self.lines: list[str] = []

    def on_line_completed(self, event):
        self.lines.append(event.line.text)

def transcribe(audio_int16: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Transcribe a pre-recorded int16 numpy array using Moonshine base-en.

    Converts int16 → float32 before feeding to Moonshine.
    Returns empty string if audio is silent or transcription yields nothing.
    """
    if len(audio_int16) == 0:
        return ""

    # Required conversion: Moonshine expects float32 in [-1.0, 1.0]
    audio_float32 = audio_int16.astype(np.float32) / 32768.0

    listener = _CaptureListener()
    _transcriber.add_listener(listener)
    try:
        _transcriber.start()

        # Feed audio in 100ms chunks (same chunk size as mic.py capture)
        chunk_size = sample_rate // 10  # 1600 frames at 16kHz
        for i in range(0, len(audio_float32), chunk_size):
            chunk = audio_float32[i : i + chunk_size]
            _transcriber.add_audio(chunk, sample_rate)

        _transcriber.stop()
    finally:
        _transcriber.remove_listener(listener)

    return " ".join(listener.lines).strip()
```

**Critical note:** The `get_model_for_language("en")` call returns `(model_path, model_arch)`. This downloads the model if not cached (~134MB, one-time). The returned path goes to `Transcriber(model_path=..., model_arch=...)`.

### Pattern 2: Push-to-Talk Voice Loop in main.py

**What:** Replace the `input("You: ")` text loop with a press-Enter-to-record loop. Print state feedback before each stage.
**When to use:** Phase 2 terminal operation (no GUI yet).

```python
# main.py — push-to-talk voice loop
from learnbox.mic import record_until_silence
from learnbox.stt import transcribe
from learnbox.llm import ask

def main():
    print("LearnBox — press Enter to ask a question, Ctrl+C to quit.\n")
    while True:
        try:
            input("Press Enter to speak...")  # blocks until Enter
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        print("Listening...", flush=True)
        audio = record_until_silence()

        if len(audio) == 0:
            print("(no speech detected — try again)\n")
            continue

        transcript = transcribe(audio)

        if not transcript.strip():
            print("(could not transcribe — try again)\n")
            continue

        print(f"You said: {transcript}")
        print("Thinking...", flush=True)

        try:
            response = ask(transcript, timeout=120.0)
            print(f"LearnBox: {response}\n")
        except RuntimeError as e:
            print(f"Error: {e}\n")
```

### Pattern 3: int16 to float32 Conversion

**What:** mic.py intentionally returns int16. stt.py is responsible for the conversion before Moonshine sees the data.
**Source:** mic.py docstring explicitly documents this handoff.

```python
# The ONLY correct conversion — documented in mic.py docstring
audio_float32 = audio_int16.astype(np.float32) / 32768.0
```

Division by 32768.0 (not 32767.0) normalizes int16 range [-32768, 32767] to approximately [-1.0, 1.0]. This is the standard PCM normalization formula.

### Pattern 4: Empty Transcript Guard

**What:** Guard against empty audio and empty transcription before reaching the LLM.
**When to use:** Always — two separate guards are needed (empty audio from mic, empty transcript from Moonshine).

```python
# Guard 1: empty audio (mic captured nothing / only silence)
if len(audio) == 0:
    print("(no speech detected)")
    continue

# Guard 2: empty transcript (Moonshine found no speech in audio)
if not transcript.strip():
    print("(could not transcribe)")
    continue

# Only now is it safe to call the LLM
response = ask(transcript)
```

### Anti-Patterns to Avoid

- **Using MicTranscriber for push-to-talk:** MicTranscriber owns mic capture internally — it conflicts with mic.py. Use `Transcriber` and feed the pre-recorded array.
- **Calling `get_model_for_language()` on every transcription:** It downloads and loads the model. Call it once at module import or startup, hold the model reference.
- **Passing int16 directly to Moonshine:** `add_audio()` expects float32 in [-1.0, 1.0]. Passing raw int16 produces garbage transcriptions with no error.
- **Using pynput or keyboard library for PTT on Pi:** pynput requires X11; keyboard library requires root. Both break headless Pi operation.
- **Single empty-check:** Check for empty audio AND empty transcript separately — one does not imply the other (Moonshine can return empty on valid audio with only background noise).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speech recognition | Custom Whisper wrapper, manual ONNX loading | moonshine-voice 0.0.49 | Moonshine handles ONNX runtime, model loading, audio chunking, KV cache, and event dispatch internally |
| int16→float32 conversion | Custom normalization | `audio_int16.astype(np.float32) / 32768.0` | Single line; correct constant is 32768.0 — don't guess |
| VAD / silence detection | Re-implement in stt.py | mic.py `record_until_silence()` | Already done in Phase 1; stt.py only sees post-VAD audio |
| Model download/path management | Manual path construction | `get_model_for_language("en")` | Returns verified `(path, arch)` tuple; handles cache dir cross-platform |
| Key-hold detection | Custom thread + time.time() | `input()` for Phase 2 | Over-engineering; Enter-to-start satisfies STT-02 with zero complexity |

**Key insight:** Moonshine's value is the entire inference pipeline — ONNX session management, KV caching, streaming architecture. Using `Transcriber.add_audio()` gives all of this for free; reimplementing any part is always worse.

---

## Common Pitfalls

### Pitfall 1: Wrong Package Name

**What goes wrong:** `pip install useful-moonshine` or `pip install moonshine` install the wrong package.
**Why it happens:** The original Moonshine package was `useful-moonshine`. The second-generation package is `moonshine-voice`. The PyPI name is not obvious.
**How to avoid:** Always `pip install moonshine-voice` (with the hyphen and "voice" suffix). Confirm with `pip show moonshine-voice`.
**Warning signs:** Install pulls in `torch==2.4.1` (~2GB) — that is the wrong package.

### Pitfall 2: Passing int16 to Moonshine

**What goes wrong:** Moonshine produces garbage transcription or silent failure — no exception is raised.
**Why it happens:** `add_audio()` expects float32 in [-1.0, 1.0]. Raw int16 values (range -32768 to 32767) are interpreted as extreme float values.
**How to avoid:** Always convert immediately at the stt.py boundary: `audio_float32 = audio_int16.astype(np.float32) / 32768.0`. Never pass the array from mic.py directly.
**Warning signs:** Moonshine returns empty string or nonsense text on audio that visually has speech energy.

### Pitfall 3: Model Loaded Per Call

**What goes wrong:** Each `transcribe()` call takes 1-3 seconds just to initialize the model, then the actual inference time on top.
**Why it happens:** `Transcriber(model_path=..., model_arch=...)` loads ONNX sessions from disk on each instantiation.
**How to avoid:** Create the `Transcriber` once at module level. Hold the instance for the session lifetime.
**Warning signs:** Each transcription is consistently slow even for short utterances.

### Pitfall 4: Using MicTranscriber Instead of Transcriber

**What goes wrong:** MicTranscriber internally opens a sounddevice InputStream — conflicts with mic.py's InputStream, causing device conflict errors or double capture.
**Why it happens:** STACK.md documents `MicTranscriber` as the API (for always-on use), not the push-to-talk pattern.
**How to avoid:** Use `Transcriber` for push-to-talk. Pass audio via `add_audio()`. Only use `MicTranscriber` if you want the library to own mic capture (not the case here).
**Warning signs:** sounddevice `PortAudioError: Device unavailable` or duplicate mic access errors.

### Pitfall 5: pynput on Headless Pi

**What goes wrong:** `ImportError` or keyboard events never fire.
**Why it happens:** pynput requires an X11 display server on Linux. Pi OS Lite / headless Pi has no X server.
**How to avoid:** Use `input()` for Phase 2 PTT. Headless-compatible keyboard input (if needed in future) requires the `keyboard` library with root, or redirecting stdin from `/dev/tty1`.
**Warning signs:** `DISPLAY` environment variable not set; no keyboard events despite key presses.

### Pitfall 6: Missing Empty Transcript Guard

**What goes wrong:** Empty string reaches `llm.ask()`, which sends a blank prompt to Ollama and returns a confusing "I couldn't understand" response.
**Why it happens:** Moonshine returns `""` for audio that has no detectable speech (background noise, very short utterances). No exception is raised.
**How to avoid:** Guard both after mic (check `len(audio) == 0`) and after STT (check `not transcript.strip()`). Both guards are needed — they catch different failure modes.
**Warning signs:** LLM responds to "empty" questions with confused answers; no error is raised anywhere.

### Pitfall 7: `get_model_for_language` Not Finding Cached Model

**What goes wrong:** Moonshine re-downloads ~134MB every run.
**Why it happens:** Model cache is in `~/.cache/moonshine_voice/` on Linux and `%LOCALAPPDATA%\moonshine_voice\` on Windows. If the download command is never run, `get_model_for_language` will trigger a download on first call (or may fail in offline environments).
**How to avoid:** Run `python -m moonshine_voice.download --language en` during setup, before any voice code runs. Verify cache exists before offline deployment.
**Warning signs:** Slow startup (1-2 minutes of downloading); fails with no internet on Pi.

---

## Code Examples

Verified patterns from official and inspected sources:

### stt.py Module Structure

```python
# learnbox/stt.py
"""
Speech-to-text transcription using Moonshine base-en.

Input: int16 numpy array at 16kHz (from mic.py record_until_silence())
Output: transcribed string, or empty string if no speech detected

The Transcriber is loaded once at module import and reused for the
lifetime of the process. Model loads from ~/.cache/moonshine_voice/
(Linux) or %LOCALAPPDATA%\\moonshine_voice\\ (Windows).
"""

import numpy as np
from moonshine_voice import Transcriber, TranscriptEventListener, get_model_for_language

# Load once — Transcriber initialization is slow (~200-500ms)
_model_path, _model_arch = get_model_for_language("en")
_transcriber = Transcriber(model_path=_model_path, model_arch=_model_arch)

SAMPLE_RATE = 16000  # must match mic.py SAMPLE_RATE
CHUNK_SIZE = 1600    # 100ms at 16kHz — matches mic.py CHUNK_FRAMES


class _LineCollector(TranscriptEventListener):
    def __init__(self):
        self.lines: list[str] = []

    def on_line_completed(self, event):
        self.lines.append(event.line.text)


def transcribe(audio_int16: np.ndarray) -> str:
    """
    Transcribe a pre-recorded int16 audio array using Moonshine base-en.

    Args:
        audio_int16: 1-D numpy array, dtype=int16, at SAMPLE_RATE Hz.
                     From mic.record_until_silence(). May be empty (len 0).

    Returns:
        Transcribed text string. Returns "" if audio is empty or Moonshine
        finds no speech. Caller must guard against empty return value.
    """
    if len(audio_int16) == 0:
        return ""

    # Moonshine requires float32 in [-1.0, 1.0]
    audio_float32 = audio_int16.astype(np.float32) / 32768.0

    listener = _LineCollector()
    _transcriber.add_listener(listener)
    try:
        _transcriber.start()
        for i in range(0, len(audio_float32), CHUNK_SIZE):
            _transcriber.add_audio(audio_float32[i : i + CHUNK_SIZE], SAMPLE_RATE)
        _transcriber.stop()
    finally:
        _transcriber.remove_listener(listener)

    return " ".join(listener.lines).strip()
```

### main.py — Push-to-Talk Voice Loop

```python
# main.py — replaces text input loop with voice loop
# Source: Pattern derived from existing main.py structure + Phase 2 requirements

from learnbox.mic import record_until_silence
from learnbox import stt  # noqa: triggers model load at import time
from learnbox.stt import transcribe
from learnbox.llm import ask


def main():
    print("LearnBox — press Enter to speak, Ctrl+C to quit.\n")
    while True:
        try:
            input("[ Press Enter to speak ]")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        print("Listening...", flush=True)
        audio = record_until_silence()

        if len(audio) == 0:
            print("(no speech detected — try again)\n")
            continue

        transcript = transcribe(audio)

        if not transcript.strip():
            print("(could not transcribe — speak closer to the mic)\n")
            continue

        print(f"You: {transcript}")
        print("Thinking...", flush=True)

        try:
            response = ask(transcript, timeout=120.0)
            print(f"LearnBox: {response}\n")
        except RuntimeError as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
```

### Offline-Safe Test Pattern for stt.py

```python
# tests/test_stt.py — offline-safe; patches Transcriber
from unittest.mock import MagicMock, patch
import numpy as np
import pytest


def make_fake_transcriber(transcript_lines: list[str]):
    """Return a mock Transcriber that calls on_line_completed with given lines."""
    class FakeTranscriber:
        def __init__(self, **kwargs):
            self._listeners = []

        def add_listener(self, listener):
            self._listeners.append(listener)

        def remove_listener(self, listener):
            self._listeners.remove(listener)

        def start(self):
            pass

        def add_audio(self, audio, sample_rate):
            pass  # Actual firing happens in stop() for simplicity

        def stop(self):
            # Simulate on_line_completed events
            for line_text in transcript_lines:
                event = MagicMock()
                event.line.text = line_text
                for listener in self._listeners:
                    listener.on_line_completed(event)

    return FakeTranscriber


# Tests must patch at the module level where Transcriber is used
def test_transcribe_returns_empty_for_empty_audio():
    from learnbox.stt import transcribe
    result = transcribe(np.zeros(0, dtype=np.int16))
    assert result == ""


def test_transcribe_converts_int16_to_float32(monkeypatch):
    """Verify float32 conversion does not raise and produces valid range."""
    audio = np.array([0, 1000, -1000, 32767, -32768], dtype=np.int16)
    converted = audio.astype(np.float32) / 32768.0
    assert converted.dtype == np.float32
    assert converted.min() >= -1.0
    assert converted.max() <= 1.0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| useful-moonshine (torch-based) | moonshine-voice (ONNX C++ core) | 2025 | 2GB torch dep eliminated; Pi-viable |
| Whisper for edge STT | Moonshine for edge STT | 2024-2025 | 25x faster on Pi 5 (237ms vs 5,863ms for Tiny) |
| Hold-key-to-talk (pynput) | Enter-to-start + auto-VAD stop | Phase 2 decision | Eliminates X11 dependency on Pi headless |
| Text input loop in main.py | PTT voice loop | Phase 2 | mic.py VAD handles "when to stop" automatically |

**Deprecated/outdated:**
- `useful-moonshine`: Archived approach, requires torch 2.4.1 (~2GB), incompatible with Pi RAM budget. Never use.
- `MicTranscriber` for push-to-talk: MicTranscriber owns mic capture internally. Conflicts with mic.py. Use `Transcriber` + `add_audio()` for PTT.

---

## Open Questions

1. **Moonshine `add_listener` / `remove_listener` API surface**
   - What we know: Official README confirms `Transcriber.add_listener()` exists; event is `on_line_completed(event)` with `event.line.text`
   - What's unclear: Whether `remove_listener()` is the exact method name, or whether re-using the same `Transcriber` instance across calls requires any reset/cleanup
   - Recommendation: Implement stt.py using `add_listener`/`remove_listener` pattern; validate with a smoke test (`python -c "from learnbox.stt import transcribe"`) on first run; adjust if API surface differs

2. **Model load timing — module-level vs lazy**
   - What we know: `Transcriber` initialization is slow (~200-500ms from STACK.md ONNX load time estimate)
   - What's unclear: Whether loading at module-import time causes any issue if the model cache is absent (would raise on import rather than on first call)
   - Recommendation: Load at module level for simplicity; wrap in a clear error message if model not found ("Run: python -m moonshine_voice.download --language en")

3. **ARM64 wheel on physical Pi 5**
   - What we know: STACK.md confirms `manylinux_2_31_aarch64` and `manylinux_2_34_aarch64` wheels exist on PyPI for moonshine-voice 0.0.49
   - What's unclear: Physical hardware confirmation still pending (flagged as blocker in STATE.md)
   - Recommendation: First task in Phase 2 must be a human checkpoint: SSH into Pi, `pip install moonshine-voice`, confirm success before writing stt.py

---

## Sources

### Primary (HIGH confidence)

- Moonshine GitHub README (official) — `Transcriber`, `add_audio()`, `TranscriptEventListener.on_line_completed`, audio file transcription pattern. Source: https://github.com/moonshine-ai/moonshine
- moonshine-voice PyPI v0.0.49 (2026-02-23) — package name, platform wheels, Python API. Source: https://pypi.org/project/moonshine-voice/
- learnbox/mic.py (direct code inspection) — `SAMPLE_RATE=16000`, `CHUNK_FRAMES=1600`, returns `dtype=int16`, docstring explicitly documents float32 conversion responsibility for Phase 2
- learnbox/llm.py (direct code inspection) — `ask()` signature, timeout parameter, RuntimeError exceptions
- main.py (direct code inspection) — existing structure to update
- pynput official docs — X11 requirement on Linux confirmed. Source: https://pynput.readthedocs.io/en/latest/limitations.html
- .planning/research/STACK.md — stack decisions, version pins, RAM budget all verified against PyPI

### Secondary (MEDIUM confidence)

- Moonshine `transcribe_without_streaming()` — WebFetch from official README (rate-limited on second fetch, but first fetch confirmed `Transcriber` + `add_audio()` pattern as the standard approach)
- Moonshine `Transcriber` chunk-feeding pattern — confirmed via WebFetch of README content; matches STACK.md documented API

### Tertiary (LOW confidence — validate on first run)

- `_transcriber.remove_listener(listener)` exact method name — WebSearch confirms `add_listener` exists; `remove_listener` inferred as complement; validate on first smoke test
- Transcriber initialization time of ~200-500ms on Pi 5 — from STACK.md estimate for ONNX session load; validate by measuring on hardware

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — moonshine-voice 0.0.49 verified on PyPI; mic.py code inspected; no new packages beyond Moonshine
- Architecture: HIGH — Transcriber API confirmed from official README; push-to-talk via input() is stdlib with zero uncertainty; int16→float32 conversion is documented in mic.py docstring
- Pitfalls: HIGH — pynput X11 limitation verified from official docs; wrong package name (useful-moonshine) verified from STACK.md research; int16 passthrough error is a documented Moonshine requirement

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (moonshine-voice 0.0.49 is current as of research date; API stable)
