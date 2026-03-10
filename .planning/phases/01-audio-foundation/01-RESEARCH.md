# Phase 1: Audio Foundation - Research

**Researched:** 2026-03-10
**Domain:** Cross-platform audio capture and playback (sounddevice / PortAudio), energy-based VAD, platform-neutral abstraction layer
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUD-01 | System captures microphone audio at 16kHz mono on both Windows and Pi 5 | sounddevice 0.5.5 InputStream with samplerate=16000, channels=1, dtype='int16'; bundles PortAudio on Windows, uses system libportaudio2 on Pi — same calling code on both |
| AUD-02 | System uses energy-based VAD to detect start and end of speech | RMS threshold loop over InputStream.read() chunks; no external VAD library needed; pattern documented below |
| AUD-03 | System plays synthesized audio through the default speaker | sd.play(array, samplerate) + sd.wait() — blocking playback via the same sounddevice library |
| AUD-04 | Audio capture and playback are abstracted behind a platform-neutral interface (Windows/Linux) | sounddevice abstracts PortAudio uniformly; never hardcode device index; use sd.query_devices() for runtime selection; same Python API on both platforms |
</phase_requirements>

---

## Summary

Phase 1 establishes the audio I/O foundation on which all subsequent phases depend. The goal is `learnbox/mic.py` (capture + VAD) and `learnbox/audio.py` (playback), both behind a platform-neutral interface, verified to work on Windows in development and confirmed installable on Pi 5. No STT, TTS, or LLM code is introduced in this phase.

The stack is a single library: `sounddevice 0.5.5`. It bundles PortAudio DLLs on Windows (zero system dependencies) and uses the system `libportaudio2` on Pi OS Bookworm (one `apt` command). The same Python API — `InputStream.read()` for capture and `sd.play()` + `sd.wait()` for playback — runs identically on both platforms. The platform abstraction requirement (AUD-04) is satisfied by sounddevice's own abstraction layer: no `if platform.system()` branches are needed in calling code.

The energy-based VAD (AUD-02) is a manual RMS threshold loop over 100ms chunks from `InputStream`. No external VAD library is needed. The pattern is straightforward: accumulate frames until N consecutive silent chunks are detected, then return the concatenated audio. The key design decisions are: never hardcode device index (use `sd.query_devices()` to find the default input), always set `samplerate=16000` explicitly (do not rely on device defaults), and always read `int16` for compatibility with the Moonshine input format required in Phase 2.

**Primary recommendation:** Implement `learnbox/mic.py` with a `record_until_silence()` function and `learnbox/audio.py` with a `play_audio()` function. Both must use sounddevice 0.5.5. Both must be tested on Windows before Phase 2 begins. Pi installation must be confirmed (run `pip install sounddevice` on actual Pi) as an explicit task in this phase.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sounddevice | 0.5.5 | Mic capture via InputStream; speaker playback via sd.play(); PortAudio bindings for both platforms | Bundles PortAudio DLLs on Windows (zero system deps); ALSA on Linux; is already a Moonshine dependency so installs automatically in later phases; same API on both platforms |
| numpy | >=1.24.0 | Audio array manipulation; RMS calculation for VAD; dtype conversion | Indirect dep of sounddevice; pin explicitly to avoid install conflicts when Moonshine is added in Phase 2 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| libportaudio2 | system | PortAudio for Linux audio I/O | Pi 5 only — `sudo apt-get install -y libportaudio2` before pip install |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sounddevice | pyaudio | pyaudio requires manual PortAudio setup on Windows; sounddevice bundles it and is a Moonshine dependency — no reason to use pyaudio |
| sounddevice | playsound | playsound 1.3.0 has known bugs on Python 3.10+, only handles file paths not arrays — incompatible with in-memory audio from Piper in Phase 3 |
| sounddevice | soundcard | soundcard is a thinner wrapper with less cross-platform testing; not a Moonshine dependency |

**Installation:**
```bash
# Windows — no system dependencies needed
pip install sounddevice numpy

# Pi 5 — system package first, then pip
sudo apt-get install -y libportaudio2
pip install sounddevice numpy
```

---

## Architecture Patterns

### Recommended Project Structure

After Phase 1 the project will look like:

```
learnbox/
├── __init__.py         # already exists
├── llm.py              # already complete — do not touch
├── mic.py              # NEW: audio capture + energy VAD
└── audio.py            # NEW: speaker playback
main.py                 # entry point — unchanged in Phase 1
requirements.txt        # add sounddevice, numpy
```

Phase 2 will add `stt.py`. Phase 3 will add `tts.py` and `pipeline.py`. Nothing from Phase 2+ is introduced here.

### Pattern 1: InputStream Read Loop with Energy VAD

**What:** Open an `InputStream` at 16kHz mono int16. Read 100ms chunks in a blocking loop. Compute RMS of each chunk. Accumulate frames until a speech segment ends (N consecutive silent chunks after speech has started).

**When to use:** This is the only capture pattern for Phase 1. Push-to-talk gating in Phase 2 will call this function after the key is pressed.

**Example:**
```python
# Source: sounddevice official docs (https://python-sounddevice.readthedocs.io)
# verified against STACK.md (HIGH confidence)
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000        # Hz — required by Moonshine (Phase 2)
CHANNELS = 1               # mono
DTYPE = "int16"            # matches Moonshine input format
CHUNK_FRAMES = 1600        # 100ms at 16kHz
SILENCE_RMS_THRESHOLD = 300  # tune on actual hardware
SILENCE_CHUNKS_REQUIRED = 10  # 1.0s of silence = end of speech
MIN_SPEECH_CHUNKS = 3       # ignore sub-300ms triggers


def record_until_silence() -> np.ndarray:
    """Capture mic audio until silence is detected. Returns int16 mono array."""
    frames = []
    speech_started = False
    silent_chunk_count = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
        # Never pass device= here — let sounddevice use the system default
    ) as stream:
        while True:
            chunk, overflowed = stream.read(CHUNK_FRAMES)
            if overflowed:
                pass  # log but do not abort
            frames.append(chunk.copy())
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            if rms >= SILENCE_RMS_THRESHOLD:
                speech_started = True
                silent_chunk_count = 0
            elif speech_started:
                silent_chunk_count += 1
                if silent_chunk_count >= SILENCE_CHUNKS_REQUIRED:
                    break
            # If speech never started and we've accumulated too many silent
            # chunks, reset — prevents unbounded accumulation before VAD fires
            if not speech_started and len(frames) > 50:
                frames = []

    return np.concatenate(frames, axis=0).flatten()
```

### Pattern 2: Blocking Playback

**What:** Play a numpy int16 array through the default output device. Block until playback is complete.

**When to use:** Used in `audio.py`. Called by `pipeline.py` in Phase 3 after TTS synthesis.

**Example:**
```python
# Source: sounddevice official docs (https://python-sounddevice.readthedocs.io)
import sounddevice as sd
import numpy as np


def play_audio(audio: np.ndarray, sample_rate: int) -> None:
    """Play audio array through default speaker. Blocks until complete."""
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
```

### Pattern 3: Device Validation at Startup

**What:** At module import or startup, query and log available audio devices. Confirm the default input device supports 16kHz. Do not hardcode device indices.

**When to use:** Add to `mic.py` as a module-level `_check_audio_device()` called once on import.

**Example:**
```python
# Source: sounddevice official docs
import sounddevice as sd


def list_audio_devices() -> None:
    """Print available audio devices. Useful for remote Pi debugging."""
    print(sd.query_devices())


def get_default_input_info() -> dict:
    """Return default input device info dict."""
    return sd.query_devices(kind="input")
```

### Anti-Patterns to Avoid

- **Hardcoding device index:** `sd.InputStream(device=0)` breaks on any machine where device 0 is not the microphone. Never do this. Let sounddevice use the system default.
- **Recording a fixed duration:** `sd.rec(int(SAMPLE_RATE * 5), ...)` always waits 5 seconds regardless of speech length. Use VAD loop instead.
- **Using float32 for the captured array:** Moonshine expects the audio as float32 in the range [-1, 1] internally, but passing int16 is fine — the conversion is trivial. However, RMS threshold values differ significantly between int16 (range ±32767) and float32 (range ±1.0). Pick one dtype and be consistent. This research uses int16 throughout mic.py; convert to float32 in stt.py if Moonshine requires it.
- **Running `sd.play()` without `sd.wait()`:** Without `sd.wait()`, the play call is non-blocking and the calling code continues immediately, potentially overlapping the next pipeline stage with audio playback.
- **Installing `useful-moonshine` instead of `moonshine-voice`:** The old PyPI package requires torch 2.4.1 (~2 GB). This phase only needs sounddevice, but document this clearly for Phase 2.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform audio I/O | Custom ALSA/WASAPI wrappers | sounddevice 0.5.5 | PortAudio handles device enumeration, sample rate negotiation, buffer management, platform differences — 10,000+ lines of C that have already been debugged |
| Sample rate resampling | Manual linear interpolation | `scipy.signal.resample_poly()` or `librosa.resample()` | Resampling has aliasing edge cases; use a library if the mic doesn't natively support 16kHz |
| Audio file I/O in tests | Manual WAV byte construction | `wave` (stdlib) or `soundfile` | Python stdlib `wave` handles WAV read/write correctly |

**Key insight:** sounddevice is the correct and only abstraction needed. It is already a Moonshine dependency, so adding it to requirements.txt in Phase 1 pre-stages the install for Phase 2 at no cost.

---

## Common Pitfalls

### Pitfall 1: Hardcoded Device Index Breaks Cross-Platform

**What goes wrong:** `sd.InputStream(device=0)` works on the development machine where device 0 is the USB mic. On a different machine or on Pi, device 0 is the HDMI audio output or a different device entirely. The stream opens without error but captures silence.

**Why it happens:** PortAudio assigns device indices based on enumeration order, which is platform and hardware-dependent.

**How to avoid:** Never pass `device=` to `InputStream` or `sd.play()`. Let sounddevice use the system default input/output. If explicit selection is needed, select by capability via `sd.query_devices()` and choose the first device that supports 16kHz input.

**Warning signs:** `record_until_silence()` returns silence or all-zeros even with active microphone. `sd.query_devices()` output on Pi shows different device ordering than on Windows.

### Pitfall 2: Sample Rate Not Supported by Device

**What goes wrong:** `sd.InputStream(samplerate=16000)` raises `sounddevice.PortAudioError: Invalid sample rate` on microphones that only support 44100Hz or 48000Hz.

**Why it happens:** USB microphones and HDMI audio devices often default to 44100 Hz. PortAudio will not silently accept a mismatched rate — it raises an error.

**How to avoid:** At startup, call `sd.query_devices(kind="input")` and check the `default_samplerate` field. If the device's default is not 16000Hz, either: (a) explicitly request 16kHz and let PortAudio negotiate (works on most devices), or (b) capture at the device's native rate and resample immediately using `scipy.signal.resample_poly()`. Log the negotiated sample rate for debugging.

**Warning signs:** `PortAudioError: Invalid sample rate` on stream open. `sd.query_devices()` shows `default_samplerate: 44100.0` for the input device.

### Pitfall 3: RMS Threshold Needs Tuning Per Environment

**What goes wrong:** A threshold of 300 (int16 RMS scale) works in a quiet office but never fires in a classroom or triggers constantly near a fan or air conditioner.

**Why it happens:** Ambient noise levels vary by environment. A static threshold cannot work universally.

**How to avoid:** Do not hardcode the threshold in the function signature's default. Expose it as a configurable parameter. Add a `calibrate_silence()` helper that samples 1 second of silence at startup and sets the threshold to 2x the measured ambient RMS. This is a single measurement, not continuous adaptive filtering.

**Warning signs:** `record_until_silence()` immediately returns empty audio in a noisy environment. Or it never returns in a very quiet environment because silence is never detected.

### Pitfall 4: Pi Install Fails Without libportaudio2

**What goes wrong:** `pip install sounddevice` on Pi OS Bookworm raises an import error at runtime: `OSError: cannot load library 'libportaudio.so.2'`.

**Why it happens:** On Linux, sounddevice does NOT bundle PortAudio (unlike Windows). The `libportaudio2` system package must be installed first.

**How to avoid:** The Pi setup task must run `sudo apt-get install -y libportaudio2` before `pip install sounddevice`. This is a known and documented requirement in the sounddevice official install docs.

**Warning signs:** `pip install sounddevice` succeeds but `import sounddevice` raises `OSError` on Pi.

### Pitfall 5: Moonshine Needs float32, Not int16

**What goes wrong:** Phase 2 will pass the `record_until_silence()` output directly to Moonshine. If `mic.py` returns int16 and the Moonshine API expects float32 normalized to [-1.0, 1.0], transcription will produce garbage silently.

**Why it happens:** The STACK.md notes that `MicTranscriber` internally uses `sounddevice.InputStream` at 16000 Hz mono **float32**. Our manual VAD loop captures int16 for efficiency. The conversion must happen at the STT boundary.

**How to avoid:** In `mic.py`, document the return dtype as `np.ndarray` with `dtype=int16`. In `stt.py` (Phase 2), add an explicit conversion before passing to Moonshine:
```python
audio_float32 = audio_int16.astype(np.float32) / 32768.0
```
This is a one-line conversion but if it is missed, the symptom is silent garbage transcriptions.

**Warning signs:** Moonshine returns empty or nonsense transcriptions for audio that sounds correct when saved to a WAV file and played back.

---

## Code Examples

Verified patterns from official sources:

### Complete mic.py Skeleton

```python
# Source: sounddevice docs (https://python-sounddevice.readthedocs.io) — HIGH confidence
# Source: ARCHITECTURE.md patterns — verified against sounddevice API
"""learnbox/mic.py — Microphone capture with energy-based VAD."""
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000       # Hz — required for Moonshine compatibility
CHANNELS = 1              # mono
DTYPE = "int16"
CHUNK_FRAMES = 1600       # 100ms per chunk at 16kHz
DEFAULT_SILENCE_RMS = 300 # int16-scale RMS; tune per environment
SILENCE_CHUNKS = 10       # 1.0s consecutive silence = end of speech
MAX_RECORD_CHUNKS = 150   # 15s max recording — prevents unbounded capture


def record_until_silence(
    silence_threshold: int = DEFAULT_SILENCE_RMS,
    silence_duration_chunks: int = SILENCE_CHUNKS,
) -> np.ndarray:
    """
    Capture microphone audio until end-of-speech detected.
    Returns int16 mono numpy array at SAMPLE_RATE.
    Raises RuntimeError if no audio device is available.
    """
    frames = []
    speech_started = False
    silent_count = 0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE) as stream:
        while len(frames) < MAX_RECORD_CHUNKS:
            chunk, _ = stream.read(CHUNK_FRAMES)
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            if rms >= silence_threshold:
                speech_started = True
                silent_count = 0
                frames.append(chunk.copy())
            elif speech_started:
                silent_count += 1
                frames.append(chunk.copy())
                if silent_count >= silence_duration_chunks:
                    break
            # Discard pre-speech silence frames to avoid feeding silence to STT

    if not frames:
        return np.zeros(0, dtype=np.int16)
    return np.concatenate(frames, axis=0).flatten()


def list_devices() -> None:
    """Print all audio devices. Use for remote Pi debugging."""
    print(sd.query_devices())
```

### Complete audio.py Skeleton

```python
# Source: sounddevice docs — HIGH confidence
"""learnbox/audio.py — Speaker playback."""
import numpy as np
import sounddevice as sd


def play_audio(audio: np.ndarray, sample_rate: int) -> None:
    """
    Play audio array through the default output device.
    Blocks until playback is complete.
    audio: numpy array, dtype int16 or float32
    sample_rate: Hz (e.g., 22050 for Piper output, 16000 for test clips)
    """
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
```

### Test Pattern — Manual Capture + Save to WAV

```python
# Verification pattern for Phase 1 success criterion testing
import wave
import numpy as np
from learnbox.mic import record_until_silence, SAMPLE_RATE

def test_capture_to_wav(output_path: str = "test_capture.wav") -> None:
    """Record audio and save to WAV file for manual playback verification."""
    print("Recording... speak now")
    audio = record_until_silence()
    print(f"Captured {len(audio)} samples ({len(audio)/SAMPLE_RATE:.1f}s)")
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    print(f"Saved to {output_path}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyAudio (PortAudio manual setup) | sounddevice (bundles PortAudio on Windows) | ~2015 | Zero Windows system deps; same library for capture and playback |
| Pywheels for sounddevice on Pi | Official PyPI aarch64 wheel | ~2020 | Standard pip install works on Pi OS without Piwheels |
| WebRTC VAD (external C library) | Energy-based RMS threshold | n/a | For push-to-talk use case, WebRTC VAD is overkill; energy threshold is sufficient and dependency-free |

**Deprecated/outdated:**
- `pyaudio`: Prefer sounddevice. PyAudio requires separate PortAudio build on Windows, is not bundled as a Moonshine dependency, and has a more complex API.
- `useful-moonshine` (PyPI): Old first-generation Moonshine package. Requires torch 2.4.1 (~2 GB). Do NOT install this package. The correct package is `moonshine-voice`.

---

## Open Questions

1. **Optimal RMS silence threshold on Pi with classroom microphone**
   - What we know: 300 (int16 RMS) works in a quiet environment
   - What's unclear: Classroom ambient noise levels could easily push ambient RMS to 400-600; the threshold must be calibrated
   - Recommendation: Implement a `calibrate_silence()` helper that samples 1s of silence at startup and sets threshold = 2x ambient RMS. Make threshold a tunable config value, not a hardcoded constant.

2. **Moonshine float32 vs int16 input format**
   - What we know: STACK.md says MicTranscriber internally uses float32. The record-then-transcribe pattern may require explicit conversion.
   - What's unclear: Whether the `Transcriber` (non-streaming) API also expects float32 or accepts int16 directly
   - Recommendation: Capture as int16 in mic.py. Add `audio.astype(np.float32) / 32768.0` conversion at the top of `stt.py` in Phase 2. This is safe regardless of which format Moonshine expects.

3. **Pi audio device name for the expected USB microphone**
   - What we know: sounddevice's default input selection works when only one input device is present
   - What's unclear: If multiple audio devices are present (e.g., HDMI audio has a capture endpoint, USB mic is plugged in), the default may not be the USB mic
   - Recommendation: Add a `--list-audio-devices` flag to `main.py` and document it in the Pi setup notes. The Pi validation task in this phase should confirm the correct device is selected.

---

## Sources

### Primary (HIGH confidence)
- sounddevice 0.5.5 official docs (https://python-sounddevice.readthedocs.io) — InputStream API, dtype options, sd.play()/sd.wait() blocking pattern, device selection via query_devices()
- sounddevice PyPI (https://pypi.org/project/sounddevice/) — v0.5.5, Windows PortAudio bundling confirmed
- sounddevice installation docs — confirmed: Windows bundles PortAudio, Pi requires `libportaudio2`
- STACK.md (project research, 2026-03-10) — Moonshine-voice 0.0.49 API pattern; Piper Python API; RAM budget verified against PyPI metadata and HuggingFace sizes
- `learnbox/llm.py` direct code inspection — confirmed synchronous httpx; `stream_ask()` available; no audio code exists yet

### Secondary (MEDIUM confidence)
- ARCHITECTURE.md (project research, 2026-03-10) — `record_until_silence()` pattern with RMS VAD; verified against sounddevice API above
- WebSearch results (2026-03-10) — confirmed sounddevice InputStream `int16` dtype is supported; confirmed RMS loop pattern is standard

### Tertiary (LOW confidence — validate before implementation)
- Moonshine `Transcriber` exact input dtype on record-then-transcribe (non-streaming) path — must be confirmed from moonshine-voice source before Phase 2 implementation
- Optimal RMS threshold for classroom microphone — must be empirically tuned on Pi hardware

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — sounddevice 0.5.5 verified from official docs and PyPI; no alternatives in scope
- Architecture patterns: HIGH — InputStream read loop and sd.play()/sd.wait() are documented sounddevice patterns; RMS VAD is a standard algorithm
- Pitfalls: HIGH — hardcoded device index, sample rate negotiation, libportaudio2 on Pi are all documented in official sounddevice install docs; Moonshine dtype boundary is a design issue flagged from STACK.md

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (sounddevice is stable; patterns do not change)
