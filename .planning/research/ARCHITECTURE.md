# Architecture Patterns: LearnBox Offline Voice Pipeline

**Domain:** Offline edge voice assistant (STT → LLM → TTS)
**Researched:** 2026-03-10
**Confidence notes:** WebSearch and WebFetch tools unavailable. All findings from training data (cutoff Aug 2025) unless flagged otherwise. Verify Moonshine and Piper API details against current official docs before implementation.

---

## Recommended Architecture

### Pipeline Overview

```
[Microphone]
     |
     | raw PCM audio (16kHz, mono, int16)
     v
[STT Component — Moonshine]
     |
     | transcript: str
     v
[LLM Component — Ollama/qwen2.5:1.5b]  (already built: learnbox/llm.py)
     |
     | response: str
     v
[TTS Component — Piper]
     |
     | synthesized audio bytes / WAV
     v
[Speaker / Audio Output]
     |
     v
[Display Component — optional, parallel]
  (shows transcript + response text)
```

### Execution Model

The pipeline is **sequential and synchronous** per turn. There is no value in parallelizing STT → LLM → TTS within a single request because each stage depends on the output of the previous. The threading model applies at the boundary between the pipeline and the UI/display, not within the pipeline itself.

**Recommended model: single main thread pipeline + optional display thread.**

```
Main thread:
  record() → transcribe() → ask() → synthesize() → play()

Display thread (optional, daemon):
  receives (transcript, response) via Queue after LLM returns
  updates screen concurrently with TTS playback
```

---

## Component Boundaries

| Component | File | Responsibility | Input | Output | Communicates With |
|-----------|------|---------------|-------|--------|-------------------|
| Audio Capture | `learnbox/mic.py` | Record mic until silence detected | hardware mic | PCM bytes (16kHz mono) | STT |
| STT | `learnbox/stt.py` | Load Moonshine model, transcribe audio | PCM bytes | `str` transcript | Pipeline orchestrator |
| LLM | `learnbox/llm.py` | Query Ollama, return response | `str` prompt | `str` response | Pipeline orchestrator |
| TTS | `learnbox/tts.py` | Synthesize speech via Piper | `str` text | WAV bytes or audio file | Audio Playback |
| Audio Playback | `learnbox/audio.py` | Play WAV through speaker | WAV bytes | — | TTS, hardware speaker |
| Pipeline | `learnbox/pipeline.py` | Orchestrate one full turn | trigger | — | All components |
| Display | `learnbox/display.py` | Show transcript + response | `(str, str)` | — | Pipeline via Queue |
| Main | `main.py` | Entry point, run loop | — | — | Pipeline |

**Boundary rule:** Each component file imports only stdlib and its own dependencies. The pipeline orchestrator imports components. Components never import each other directly.

---

## Data Flow

### Turn lifecycle (one question → one answer)

```
1. CAPTURE
   mic.py: open audio stream (PyAudio or sounddevice)
            record frames until VAD detects end-of-speech
            return: raw_audio: bytes (16kHz, mono, int16)

2. TRANSCRIBE
   stt.py: pass raw_audio to Moonshine model
            model runs synchronously (blocking, ~0.5–2s on Pi 5)
            return: transcript: str

3. GATE (empty transcript check)
   pipeline.py: if transcript.strip() == "": go back to step 1
                else: continue

4. GENERATE
   llm.py: POST to Ollama (stream=False, blocking, ~3–8s on Pi 5)
            return: response: str
            (stream=True variant exists but not needed — response is short)

5. SYNTHESIZE
   tts.py: pass response text to Piper subprocess or Python binding
            return: audio_data: bytes (WAV)

6. PLAY
   audio.py: play WAV bytes through system audio output (blocking until done)

7. [PARALLEL, optional] DISPLAY
   display.py: receives (transcript, response) via Queue after step 4
               renders to screen while step 5+6 run
```

### Data types between boundaries

| Boundary | Type | Format |
|----------|------|--------|
| Mic → STT | `bytes` or `np.ndarray` | 16kHz, mono, int16 PCM |
| STT → Pipeline | `str` | plain transcript text |
| Pipeline → LLM | `str` | plain question text |
| LLM → Pipeline | `str` | plain answer text |
| Pipeline → TTS | `str` | plain answer text |
| TTS → Playback | `bytes` or file path | WAV (16kHz or 22kHz mono) |
| Pipeline → Display | `tuple[str, str]` | (transcript, response) via Queue |

---

## Threading / Async Model

### Recommendation: synchronous pipeline, no asyncio

The `llm.py` module already uses synchronous `httpx`. Moonshine and Piper both have synchronous Python APIs. **Do not introduce asyncio** — it adds complexity with no benefit when all stages are sequential and none are I/O-concurrent within a turn.

**Confidence:** MEDIUM — verified that `llm.py` is synchronous; Moonshine/Piper sync API confirmed by training data but should be verified against current docs.

### Why not asyncio

- All three blocking operations (record, transcribe, synthesize) use C extensions or subprocess — they do not release the GIL in a way asyncio can exploit.
- Asyncio would require `run_in_executor` for every blocking call, adding complexity with no throughput benefit for a single-user device.
- The pipeline is inherently sequential: output of each stage feeds the next.

### Threading model for display

If a screen is attached, use a single daemon thread consuming a `queue.Queue`:

```python
import queue, threading

display_queue = queue.Queue()

def display_worker(q):
    while True:
        item = q.get()
        if item is None:
            break
        transcript, response = item
        render_to_screen(transcript, response)

threading.Thread(target=display_worker, args=(display_queue,), daemon=True).start()
```

The main pipeline thread puts `(transcript, response)` into the queue right after the LLM returns, so display updates concurrently with TTS playback. This is the only parallelism needed.

---

## Moonshine STT: Integration Details

**Confidence:** LOW — training data only. Verify against https://github.com/usefulsensors/moonshine before coding.

### What is known

- Moonshine is a small Transformer-based ASR model designed for edge deployment.
- Two model sizes: `moonshine/tiny` (~27M params, ~40MB) and `moonshine/base` (~61M params, ~90MB).
- Python package: `useful-moonshine` (pip installable).
- Input: 16kHz mono float32 numpy array.
- Output: string transcript.
- Runs via ONNX Runtime on CPU — no GPU required.

### Likely Python usage pattern (LOW confidence — verify)

```python
from moonshine import Moonshine

model = Moonshine("moonshine/tiny")  # load once at startup
transcript = model.transcribe(audio_np)  # blocking call, returns str
```

### RAM estimate

- Model weights: ~40MB (tiny) or ~90MB (base).
- ONNX Runtime overhead: ~80–120MB.
- Total STT footprint: ~120–200MB depending on model size.
- **Use `moonshine/tiny` on Pi 5 to stay within RAM budget.**

### VAD (Voice Activity Detection)

Moonshine does not include built-in VAD. The capture component must implement silence detection before calling transcribe. Recommended approach: energy-based threshold (RMS) or `webrtcvad` (lightweight C extension).

- Record until N consecutive silent frames detected.
- Trim leading/trailing silence before passing to Moonshine.
- Max recording window: 10–15s to bound memory.

---

## Piper TTS: Integration Details

**Confidence:** LOW — training data only. Verify against https://github.com/rhasspy/piper before coding.

### What is known

- Piper is a fast neural TTS system designed for local/offline use.
- Provides a command-line binary and a Python binding (`piper-tts` pip package, or via `piper` binary subprocess).
- Models are ONNX-based, voice-specific (separate `.onnx` + `.json` config file per voice).
- English voices: `en_US-lessac-medium` is a commonly cited quality/size balance (~60MB).
- Output: 16kHz or 22kHz mono WAV.

### Two valid integration approaches

**Option A: Subprocess (safer, no Python binding version pinning)**

```python
import subprocess, io

def synthesize(text: str, model_path: str) -> bytes:
    result = subprocess.run(
        ["piper", "--model", model_path, "--output-raw"],
        input=text.encode(),
        capture_output=True,
    )
    return result.stdout  # raw PCM or WAV bytes
```

**Option B: Python binding (cleaner, one process)**

```python
from piper import PiperVoice

voice = PiperVoice.load("en_US-lessac-medium.onnx", config_path="en_US-lessac-medium.onnx.json")
audio_bytes = b"".join(voice.synthesize_stream_raw(text))
```

**Recommendation: Use subprocess for the first build.** The Piper binary is stable and well-tested on Pi. Switch to the Python binding only if subprocess latency is a problem.

### RAM estimate

- Piper binary process: ~50–80MB.
- Voice model (medium quality): ~60–80MB.
- Total TTS footprint: ~120–160MB.

---

## Audio Capture: Integration Details

**Confidence:** MEDIUM — well-established patterns, two solid options.

### Option A: sounddevice (recommended)

```python
import sounddevice as sd
import numpy as np

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"

def record_until_silence(silence_threshold=500, silence_duration=1.0) -> np.ndarray:
    frames = []
    silent_frames = 0
    frames_per_check = int(SAMPLE_RATE * 0.1)  # 100ms chunks
    required_silent = int(silence_duration / 0.1)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE) as stream:
        while True:
            chunk, _ = stream.read(frames_per_check)
            frames.append(chunk)
            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
            if rms < silence_threshold:
                silent_frames += 1
            else:
                silent_frames = 0
            if silent_frames >= required_silent and len(frames) > required_silent:
                break

    return np.concatenate(frames, axis=0).flatten()
```

`sounddevice` works on Linux (ALSA), macOS, and Windows without PulseAudio dependencies — important for Pi 5.

### Option B: PyAudio

More widely documented but requires PortAudio which can have installation issues on Pi OS. Prefer `sounddevice`.

---

## Audio Playback: Integration Details

**Confidence:** MEDIUM — standard pattern.

```python
import sounddevice as sd
import numpy as np
import io, wave

def play_wav(wav_bytes: bytes):
    with wave.open(io.BytesIO(wav_bytes)) as wf:
        rate = wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    sd.play(data, samplerate=rate)
    sd.wait()  # blocking until playback complete
```

Using the same `sounddevice` for both capture and playback eliminates a dependency. `sd.wait()` blocks the pipeline thread cleanly while audio plays.

---

## RAM Budget (Pi 5, 2GB)

The Pi 5 with 2GB RAM has approximately 1.7GB usable after OS overhead (~300MB for Pi OS Lite).

| Component | Estimated RAM | Notes |
|-----------|---------------|-------|
| Pi OS Lite baseline | ~300 MB | Headless recommended |
| Ollama daemon | ~600–700 MB | qwen2.5:1.5b quantized (Q4) model weights |
| Moonshine tiny (ONNX) | ~150–200 MB | Includes ONNX Runtime |
| Piper subprocess | ~120–160 MB | Binary + voice model |
| Python interpreter + app | ~50–80 MB | Main process + libraries |
| sounddevice / audio | ~10–20 MB | PortAudio, numpy |
| Display (if tkinter/framebuffer) | ~30–60 MB | Optional; use framebuffer not full X11 |
| **Total estimated** | **~1260–1420 MB** | **Fits within ~1700 MB usable** |
| **Headroom** | **~280–440 MB** | Buffer for numpy temp arrays, pip, etc. |

**Key constraint:** Ollama must be running before the Python app starts. The Python app never loads the LLM weights — it only sends HTTP requests to Ollama's daemon on localhost:11434.

**Critical:** If Moonshine `base` is used instead of `tiny`, add ~80MB. Still fits, but reduces headroom. Start with `tiny`.

**Confidence:** LOW-MEDIUM — Ollama memory figures verified approximately against known qwen2.5:1.5b GGUF sizes (~900MB file, Q4 ~600–700MB in RAM). Moonshine/Piper figures from training data; measure on actual hardware.

---

## Build Order

Build in dependency order. Each stage is testable in isolation before adding the next.

```
Stage 1: Audio Capture (mic.py)
  Test: record 5s of audio, save to WAV file, confirm it sounds correct
  Dependency: sounddevice, numpy
  No other LearnBox components needed

Stage 2: STT (stt.py)
  Test: pass WAV file from Stage 1 to Moonshine, print transcript
  Dependency: moonshine package, Stage 1 output as test input
  No other LearnBox components needed

Stage 3: TTS (tts.py + audio.py)
  Test: pass a hardcoded string to Piper, hear it spoken
  Dependency: piper binary or package, sounddevice
  LLM not needed for this stage

Stage 4: Pipeline wiring (pipeline.py)
  Wire: mic.py → stt.py → llm.py → tts.py → audio.py
  Test: full end-to-end voice turn
  Dependency: all previous stages + existing llm.py

Stage 5: Robustness
  Add: empty transcript gate, LLM error handling, audio device error recovery
  Add: "thinking..." audio cue (short beep or synthesized phrase) played after STT
       so user knows the system heard them while LLM runs

Stage 6: Display (display.py) — optional
  Add: queue-based display thread, render question + answer to screen
  Dependency: full pipeline from Stage 4

Stage 7: Pi 5 validation
  Measure: RAM usage, end-to-end latency, thermal behavior under sustained use
```

**Stage 3 before Stage 4 matters:** You want to confirm TTS works before wiring it into the full pipeline, otherwise pipeline failures are ambiguous (is it STT, LLM, or TTS?).

---

## Patterns to Follow

### Pattern 1: Load Models Once at Startup

**What:** Instantiate Moonshine and Piper (if using Python binding) once at application start, not per-turn.
**When:** Always — model loading takes 1–5 seconds and allocates the bulk of RAM.
**Why:** Loading inside the per-turn function causes 2–5x latency spike per turn and risks OOM from multiple allocations.

```python
# In pipeline.py __init__ or module-level setup
stt_model = MoonshineModel.load("moonshine/tiny")
tts_voice = PiperVoice.load("en_US-lessac-medium.onnx")

def run_turn():
    audio = record_until_silence()
    transcript = stt_model.transcribe(audio)
    response = ask(transcript)
    audio_out = tts_voice.synthesize(response)
    play_wav(audio_out)
```

### Pattern 2: Subprocess Piper with Stdin/Stdout

**What:** If using Piper via subprocess, keep the subprocess alive between turns using `Popen` with stdin pipe, not spawning a new process per turn.
**Why:** Process spawn overhead is ~200–500ms. On Pi 5 this is noticeable.

### Pattern 3: Energy-Based VAD Before Moonshine

**What:** Only call `transcribe()` if audio exceeds an RMS threshold. If the captured audio is silence (user didn't speak), discard and re-record.
**Why:** Moonshine will attempt to transcribe silence and return garbage tokens, which then get sent to the LLM.

### Pattern 4: "Thinking" Feedback Cue

**What:** After STT returns a non-empty transcript, immediately play a short audio cue (e.g., synthesize "one moment" or a tone) before calling the LLM.
**Why:** LLM inference takes 3–8s on Pi 5. Without feedback the device appears frozen. This is a UX-critical pattern for student use.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Streaming LLM into TTS

**What:** Piping streaming LLM tokens directly into TTS as they arrive.
**Why bad:** Piper needs complete sentences (or at least phrase boundaries) to produce natural-sounding speech. Streaming individual tokens produces choppy, broken audio. Additionally, `learnbox/llm.py` already constrains responses to 2–3 sentences, making full-response TTS latency acceptable (~3–8s LLM + ~0.5–1s TTS).
**Instead:** Use `stream=False` in `llm.py` (already the default in `ask()`). Synthesize the full response in one call.

### Anti-Pattern 2: asyncio for the Pipeline

**What:** Wrapping all pipeline stages in `async def` and using `asyncio.gather`.
**Why bad:** All blocking operations (audio I/O, Moonshine inference, Piper synthesis) use C extensions that block the event loop. You'd need `run_in_executor` everywhere, which is equivalent to threading but harder to reason about.
**Instead:** Synchronous pipeline in main thread. Use `threading.Thread` only for the display update if needed.

### Anti-Pattern 3: Recording Fixed Duration Audio

**What:** `sd.rec(int(SAMPLE_RATE * 5), ...)` — always recording 5 seconds.
**Why bad:** Students asking one-word answers wait 5s every time. Students with longer questions get cut off.
**Instead:** Energy-based VAD with silence timeout as described above.

### Anti-Pattern 4: Running Ollama Inside the Python Process

**What:** Using `subprocess.run(["ollama", "run", ...])` to launch the LLM from within the app.
**Why bad:** LLM loading takes 10–30s on Pi 5 and Ollama is designed as a persistent daemon.
**Instead:** Start Ollama as a systemd service at Pi boot. The Python app only sends HTTP requests to the already-running daemon. The `learnbox/llm.py` `ConnectError` handler already surfaces this correctly.

### Anti-Pattern 5: Using Pi OS Desktop (Full X11)

**What:** Running LearnBox inside a desktop environment GUI.
**Why bad:** X11 + desktop environment consumes ~200–400MB RAM, directly threatening the pipeline's headroom.
**Instead:** Pi OS Lite (headless). If display is needed, use the Linux framebuffer (`/dev/fb0`) with a lightweight library (e.g., `pygame` in framebuffer mode, or direct framebuffer write), not a full desktop session.

---

## `pipeline.py` Skeleton

This is the orchestration module that should be created in Stage 4.

```python
"""learnbox/pipeline.py — Orchestrates one full voice turn."""
import queue
import threading
from learnbox.mic import record_until_silence
from learnbox.stt import transcribe
from learnbox.llm import ask
from learnbox.tts import synthesize
from learnbox.audio import play_wav

class Pipeline:
    def __init__(self, display_queue: queue.Queue | None = None):
        self.display_queue = display_queue
        # Models loaded once here (see Pattern 1)
        self._init_models()

    def _init_models(self):
        # Load Moonshine and Piper once at startup
        from learnbox.stt import load_model as load_stt
        from learnbox.tts import load_voice as load_tts
        self.stt_model = load_stt()
        self.tts_voice = load_tts()

    def run_turn(self) -> tuple[str, str] | None:
        """One full turn: listen → transcribe → generate → speak."""
        audio = record_until_silence()
        transcript = transcribe(audio, self.stt_model)
        if not transcript.strip():
            return None  # Silence detected, skip turn

        response = ask(transcript)

        if self.display_queue:
            self.display_queue.put((transcript, response))

        audio_out = synthesize(response, self.tts_voice)
        play_wav(audio_out)
        return transcript, response

    def run_forever(self):
        while True:
            try:
                self.run_turn()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Pipeline error: {e}")
                # Continue — don't crash on transient errors
```

---

## Scalability / Portability Notes

This is a single-user, single-device system. "Scalability" means ensuring it degrades gracefully under hardware constraints, not multi-user scaling.

| Concern | Pi 5 (current target) | Development (Windows) |
|---------|----------------------|----------------------|
| Audio device | ALSA / USB mic | Windows audio / virtual mic |
| Ollama | Runs as daemon | Runs as system tray app |
| Moonshine | ONNX Runtime on ARM64 | ONNX Runtime on x86-64 |
| Piper | ARM64 binary available | Windows binary available |
| Display | Framebuffer or HDMI | Console or tkinter |
| RAM | Hard 2GB limit | Effectively unlimited |

**Both platforms use the same Python code.** Audio device differences are handled by `sounddevice` abstraction. No platform-specific branches needed in the pipeline.

---

## Sources

| Claim | Confidence | Source |
|-------|------------|--------|
| Moonshine model sizes, ONNX Runtime, Python API | LOW | Training data (Aug 2025) — verify: https://github.com/usefulsensors/moonshine |
| Piper subprocess/Python API, WAV output | LOW | Training data (Aug 2025) — verify: https://github.com/rhasspy/piper |
| Ollama qwen2.5:1.5b RAM ~600-700MB | MEDIUM | Known GGUF Q4 file sizes, training data |
| sounddevice ALSA/Windows compatibility | MEDIUM | Training data, well-established library |
| `learnbox/llm.py` is synchronous, uses httpx | HIGH | Direct code inspection |
| llm.py stream=False default in ask() | HIGH | Direct code inspection |
| Sequential pipeline is correct model for this pipeline | HIGH | Logical dependency: each stage's output is the next stage's input |
| Pi OS Lite RAM savings vs desktop | MEDIUM | Established Linux baseline, training data |
