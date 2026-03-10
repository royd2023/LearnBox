# Domain Pitfalls: Offline Voice Pipeline (LearnBox)

**Domain:** Offline voice pipeline on constrained edge hardware (Raspberry Pi 5, 2GB RAM)
**Researched:** 2026-03-10
**Stack:** Moonshine (STT) + Ollama/qwen2.5:1.5b (LLM) + Piper (TTS), Python
**Confidence:** MEDIUM — web fetch and search tools unavailable; findings based on official GitHub documentation patterns, known Pi hardware constraints, and training knowledge of each component. Flag anything marked LOW for validation before implementation.

---

## Critical Pitfalls

Mistakes that cause rewrites, OOM crashes, or pipeline deadlock on Pi 5.

---

### Pitfall 1: All Three Models Loaded in RAM Simultaneously

**What goes wrong:** Moonshine, Ollama (qwen2.5:1.5b), and Piper are each loaded into memory at startup. On Pi 5 with 2GB RAM, this causes OOM kills or severe thrashing before a single request completes.

**Why it happens:** The intuitive approach is to initialize all pipeline components on startup for lowest latency. Developers test on Windows (16GB+ RAM) where this works fine, then deploy to Pi and find the system unresponsive.

**Memory budget reality (MEDIUM confidence):**
- Moonshine tiny: ~50-100MB
- Moonshine base: ~200-400MB
- qwen2.5:1.5b via Ollama: ~900MB-1.1GB (quantized GGUF on Pi)
- Piper TTS model (medium voice): ~60-130MB
- Python interpreter + libraries + OS overhead: ~200-400MB
- **Total estimate: 1.4–2.0GB** — leaving nearly zero headroom on 2GB

**Consequences:** Random OOM kills mid-request, pipeline stalls, need for complete architectural redesign after integration.

**Prevention:**
- Use Moonshine `tiny` model, not `base`, on Pi 5 to save ~150-200MB
- Use Piper's smallest English voice model (under 70MB)
- Load Moonshine only when mic input starts; unload (del + gc.collect()) before Ollama inference if memory is tight
- Measure RAM at each pipeline stage with `psutil` before integrating on Pi
- Set `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1` to prevent Ollama from caching multiple models

**Detection (warning signs):**
- `dmesg | grep -i "out of memory"` on Pi shows OOM killer firing
- `free -m` shows <100MB available during inference
- System becomes unresponsive for 10-30s then recovers (swap thrash)
- Ollama returns 500 errors without obvious cause

**Phase:** Must be validated in Phase 1 (pipeline integration). Do not defer to later.

---

### Pitfall 2: Windows Audio Stack Incompatible With Pi Linux Audio Stack

**What goes wrong:** Microphone capture and speaker output code written on Windows (using `sounddevice`, `pyaudio`, or `soundcard`) uses Windows audio APIs (WASAPI/DirectSound). On Pi, the same code fails silently or raises cryptic ALSA/PulseAudio errors.

**Why it happens:** `sounddevice` and `pyaudio` abstract the OS audio layer but device names, sample rate support, and default device enumeration differ completely between Windows and Linux. A device index of `0` on Windows means something entirely different than on Pi.

**Consequences:** Audio capture works in dev, fails in prod. The code looks correct but produces silence or crashes at runtime on the Pi. Debugging requires physical access to the Pi.

**Prevention:**
- Never hardcode device index or device name strings
- Use `sounddevice.query_devices()` at startup to enumerate and select by capability (default input, sample rate 16000Hz)
- Abstract mic capture behind a `MicrophoneCapture` class that resolves the device at runtime
- Test audio capture in CI by mocking the audio layer from day 1
- Validate ALSA/PulseAudio device availability on Pi before implementing audio code on Windows
- Add a `--list-audio-devices` CLI flag early so the Pi deployment can be diagnosed remotely

**Detection (warning signs):**
- `sounddevice.PortAudioError: [Errno -9999]` or similar on Pi
- Moonshine receives empty or all-zero audio arrays
- No audio playback despite Piper generating output correctly

**Phase:** Address in Phase 1 (audio I/O layer). Platform abstraction must be built before Moonshine integration.

---

### Pitfall 3: Blocking Pipeline Architecture — No Streaming, 15s+ Perceived Latency

**What goes wrong:** The natural sequential implementation is: record audio → wait → transcribe → wait → LLM generate → wait → synthesize → wait → play. Each step blocks. On Pi 5, the LLM alone takes 3-8s, STT ~1-2s, TTS ~1-2s. Total: 5-12s of complete silence before the student hears anything. This feels broken to a child.

**Why it happens:** The current codebase already uses `stream=False` in `ask()` with a 120s timeout. This is fine for text I/O but unacceptable for voice UX where silence feels like a crash.

**Consequences:** Students press the button again thinking it failed, causing duplicate requests. Interaction feels broken. The <10s latency target in PROJECT.md becomes impossible to achieve reliably on Pi 5.

**Prevention:**
- Use `stream_ask()` (already implemented in `llm.py`) rather than `ask()` for voice mode
- Start Piper TTS on the first complete sentence from the LLM stream, not after the full response
- Provide an immediate audio acknowledgment ("hmm", "let me think") within 500ms of STT completion so silence is never longer than that
- Overlap phases: while Piper speaks sentence 1, the LLM is generating sentence 2
- Keep LLM responses to 2-3 sentences (already enforced by system prompt) — critical for latency

**Detection (warning signs):**
- End-to-end latency consistently >8s in testing
- `stream_ask()` in `llm.py` is never called in the voice pipeline implementation
- No "thinking" audio cue in the UX design

**Phase:** Architecture decision must be made in Phase 1 design. Retrofitting streaming into a blocking pipeline is painful.

---

### Pitfall 4: Moonshine ARM Wheel Availability — Installation Fails on Pi

**What goes wrong:** Moonshine depends on ONNX Runtime and may have TensorFlow/PyTorch dependencies that either don't have ARM64 wheels on PyPI or require specific versions. `pip install` succeeds on Windows x86-64, then fails on Pi ARM64 with "no matching distribution found" or C extension compilation errors.

**Why it happens:** Python package availability on ARM64/aarch64 Linux lags behind x86-64. The Raspberry Pi OS (Bookworm/64-bit) runs aarch64 but many ML packages only publish x86-64 wheels. Source builds require build tools and can take 30+ minutes.

**Consequences:** Hours lost on Pi trying to install Moonshine. May require switching to a different STT solution if wheels are permanently unavailable.

**Prevention (MEDIUM confidence — requires validation on actual Pi):**
- Verify Moonshine installation on Pi before committing to it in the roadmap
- Test with a fresh Pi OS image: `pip install useful-moonshine` and confirm all dependencies resolve
- Check that `onnxruntime` has an ARM64 wheel for the target Python version (3.11/3.12)
- If standard install fails, try the `onnxruntime` package from Raspberry Pi's own Piwheels: `https://www.piwheels.org/`
- Pin exact working versions in `requirements.txt` once confirmed, never use `>=` without upper bound on Pi
- Have a fallback plan: `faster-whisper` (Whisper-based, has ARM64 ONNX wheels via CTranslate2)

**Detection (warning signs):**
- `pip install` output contains "Building wheel for..." for core dependencies (slow, may fail)
- Error: `ERROR: Could not find a version that satisfies the requirement onnxruntime`
- Any C/C++ compilation error during pip install

**Phase:** Must be validated in Phase 0 (environment setup on Pi), before writing any Moonshine integration code.

---

### Pitfall 5: Ollama Model Pull Requires Internet — Breaks Offline Deployment

**What goes wrong:** Ollama downloads models from the internet on first use via `ollama pull qwen2.5:1.5b`. In a truly offline deployment scenario (school with no internet, remote village), this step is impossible. If the model isn't pre-loaded, Ollama returns an error and the pipeline fails.

**Why it happens:** Developers run `ollama pull` on their machine during development and forget this won't happen in offline deployment. The Pi ships without the model and the first run fails.

**Consequences:** Device is bricked in offline deployment until someone connects it to internet. Contradicts the core "fully offline" requirement.

**Prevention:**
- Pre-pull the model during Pi setup/imaging: `ollama pull qwen2.5:1.5b` must be in the deployment script
- Verify the model is present at startup: check `ollama list` output or `~/.ollama/models/` directory before accepting voice input
- Include model verification in the Pi setup checklist and startup health check
- Consider packaging the model in the deployment image so `ollama serve` finds it without a pull

**Detection (warning signs):**
- Ollama returns `{"error":"model 'qwen2.5:1.5b' not found, try pulling it first"}`
- `~/.ollama/models/` directory is empty or smaller than expected (~900MB)
- Health check script missing Ollama model verification step

**Phase:** Deployment script (Phase 3 or final integration). Must be in the Pi setup checklist.

---

### Pitfall 6: Piper TTS Voice Model Not Bundled — First-Run Download Fails Offline

**What goes wrong:** Piper requires a separate voice model file (`.onnx` + `.onnx.json`). The Piper binary itself does not include any voice. If the voice model isn't present, Piper exits with an error. Like Ollama, this download requires internet and silently fails in offline environments.

**Why it happens:** Piper's README describes downloading voice models from Hugging Face or the Piper releases page. Developers do this once and forget. The Pi image ships without the voice file.

**Consequences:** Piper cannot produce any audio. The TTS stage of the pipeline produces silent output or crashes. This is especially insidious because the error may not propagate clearly to the user.

**Prevention:**
- Download the target voice model during Pi setup (e.g., `en_US-lessac-medium.onnx`) and commit its path to config
- Include voice model path verification in startup health check
- Store the voice model in the repo or deployment package, not relying on a runtime download
- Use only one voice model to minimize storage footprint (Piper voices are 60-130MB each)

**Detection (warning signs):**
- Piper exits with code 1 immediately with no audio output
- Error message referencing missing `.onnx` file path
- `ls` of the expected voice directory shows no `.onnx` files

**Phase:** Pi environment setup (same as Ollama model pre-pull). Must be in deployment checklist.

---

## Moderate Pitfalls

Mistakes that cause significant debugging time but don't require rewrites.

---

### Pitfall 7: Sample Rate Mismatch Between Mic Capture and Moonshine Input

**What goes wrong:** Moonshine expects audio at 16000Hz (16kHz). Many USB microphones or HDMI capture devices default to 44100Hz or 48000Hz. The audio is captured at the wrong rate, fed to Moonshine, and transcription produces garbage text or empty strings — with no error raised.

**Prevention:**
- Always explicitly set `samplerate=16000` in `sounddevice.rec()` or equivalent
- Verify captured audio shape: `(n_samples,)` where `n_samples ≈ 16000 * duration_seconds`
- If the mic doesn't support 16kHz natively, resample using `librosa.resample()` or `scipy.signal.resample_poly()` immediately after capture
- Log the actual captured sample rate at startup during development

**Detection:** Moonshine returns empty strings or nonsense transcriptions for clearly spoken audio. `sounddevice.query_devices()` shows device's default sample rate is not 16000Hz.

**Phase:** Phase 1 (STT integration). Add sample rate assertion in the test suite.

---

### Pitfall 8: Piper Subprocess Overhead on Every Utterance

**What goes wrong:** Piper is typically invoked as a command-line subprocess: `piper --model en_US-lessac-medium.onnx < text.txt | aplay`. Spawning a new process for every TTS response adds 0.5-1.5s of subprocess startup overhead on Pi, and creates complexity around stdin/stdout piping and error handling.

**Prevention:**
- Keep Piper as a long-running subprocess with stdin piping, not a fresh spawn per utterance (requires subprocess management with `Popen`)
- Alternatively, investigate Piper's Python bindings (`piper-tts` PyPI package) which load the model once in-process and call it repeatedly — eliminates subprocess overhead
- Cache the subprocess handle across calls; only restart it if it dies

**Detection:** Each TTS call takes 1-2s longer than expected. `strace` or `time` shows most time spent in process startup, not inference.

**Phase:** Phase 2 (TTS integration). Architecture decision before first implementation.

---

### Pitfall 9: No Input Validation Between Pipeline Stages

**What goes wrong:** Moonshine returns an empty string (silence, background noise, or failed transcription). This empty string is passed directly to Ollama, which responds with "I'm not sure what you're asking" or similar. Piper then speaks a confused response. The student hears garbage.

**Prevention:**
- After Moonshine transcription, validate: strip whitespace, check minimum length (e.g., >3 characters), check confidence score if available
- If transcription is empty or below threshold, re-prompt the student: play a "I didn't catch that" audio clip (pre-recorded, not TTS) for speed
- Never pass an empty or whitespace-only string to Ollama
- Add logging at each pipeline stage boundary for debugging

**Detection:** Ollama generates "could you repeat that?" style responses during testing with silence or background noise. Empty transcriptions reach Ollama.

**Phase:** Phase 1-2 (integration). Add guard assertions at every stage boundary.

---

### Pitfall 10: Ollama Flash Attention / GPU Layer Config Incompatible With Pi

**What goes wrong:** Ollama on Pi 5 may default to CPU-only inference. Attempting to enable GPU offloading with `OLLAMA_NUM_GPU=1` on Pi 5 (which has no discrete GPU, only VideoCore VII) either does nothing or causes errors. Developers who test Ollama GPU acceleration on their dev machine may inadvertently set env vars that break Pi.

**Prevention:**
- Do not set `OLLAMA_NUM_GPU` on Pi 5 — CPU inference is the only supported mode
- Set `OLLAMA_NUM_THREADS` to match Pi 5's 4 cores (e.g., `OLLAMA_NUM_THREADS=4`) for optimal CPU utilization
- Keep Ollama environment config in a `.env` file separate for Pi vs. Windows dev
- On Pi, set `OLLAMA_FLASH_ATTENTION=0` explicitly if flash attention causes instability (LOW confidence — verify on Pi)

**Detection:** Ollama logs show GPU initialization errors or extremely slow inference (~50+ seconds per token). `ollama ps` shows unexpected resource usage.

**Phase:** Phase 1 (Ollama Pi deployment). Verify config before LLM integration.

---

### Pitfall 11: Windows/Linux Path and Binary Differences Break Cross-Platform Code

**What goes wrong:** Piper binary is `piper.exe` on Windows and `piper` on Linux. Audio device names use `\\Device\\` paths on Windows and `/dev/` on Linux. Hardcoded paths in config or code cause KeyError or FileNotFoundError on one platform.

**Prevention:**
- Use `platform.system()` to select the correct binary name and paths
- Store all platform-specific config in `config.json` (already exists in project) with separate `windows` and `linux` sections
- Use `pathlib.Path` throughout (already common Python practice) — never concatenate paths with strings
- Test the full pipeline on both platforms before declaring a feature complete

**Detection:** `FileNotFoundError: piper.exe` on Linux or vice versa. Any hardcoded platform-specific path in source code.

**Phase:** Phase 1 (environment abstraction). Must be resolved before cross-platform audio/TTS work begins.

---

## Minor Pitfalls

Annoyances that slow development but have clear fixes.

---

### Pitfall 12: LLM Response Contains Markdown That Breaks TTS

**What goes wrong:** qwen2.5 sometimes returns responses with markdown formatting: `**bold**`, `- bullet points`, `# headings`. Piper reads these as literal text: "asterisk asterisk bold asterisk asterisk". This is jarring and unprofessional in a voice interface.

**Prevention:**
- Strip markdown before passing to Piper: remove `*`, `#`, `-` list bullets, backticks
- The system prompt already says "2-3 sentences maximum" — add explicit "no markdown formatting, no bullet points, no bold or italic text" to the system prompt
- Add a `clean_for_speech()` utility function with regex stripping and a test suite

**Detection:** "Asterisk", "hashtag", "backtick" audible in TTS output during manual testing.

**Phase:** Phase 2 (LLM↔TTS integration). Easy fix, but easy to miss without audio testing.

---

### Pitfall 13: Microphone Sensitivity / Noise Floor Causes Always-Listening Loops

**What goes wrong:** If using voice activity detection (VAD) to trigger recording, a low noise floor or sensitive mic causes false triggers: a fan, keyboard click, or air conditioner registers as speech. Moonshine transcribes it as nonsense, which gets sent to the LLM.

**Prevention:**
- Use WebRTC VAD or `silero-vad` for robust voice activity detection rather than amplitude threshold only
- Tune VAD aggressiveness parameter (0-3 scale) on the actual Pi hardware with the actual microphone
- Add a minimum audio energy threshold below VAD to gate obvious silence
- Test in the target deployment environment noise conditions (classroom, not anechoic chamber)

**Detection:** LLM queries arriving with no button press from the user. Ollama logs show requests every few seconds during silence.

**Phase:** Phase 2 (full pipeline integration). Lower priority if using push-to-talk button trigger instead of VAD.

---

### Pitfall 14: Ollama Context Length Accumulates Across Turns

**What goes wrong:** If the pipeline is extended to support multi-turn conversation by passing conversation history to Ollama, the context grows with each turn. On qwen2.5:1.5b with limited context window and constrained RAM, long conversations cause slowdowns and eventually OOM or dropped context.

**Prevention:**
- For v1 (LearnBox), treat each question as stateless — do not accumulate conversation history
- The current `llm.py` `ask()` function already does this correctly (no history)
- If multi-turn is added later, cap history at last 2 exchanges maximum
- Never store raw transcription history in memory without a max-length guard

**Detection:** Response latency grows with each question in a session. Memory usage grows monotonically across questions.

**Phase:** Not an issue for v1. Guard against it if multi-turn conversation is ever added.

---

### Pitfall 15: Pi 5 Thermal Throttling Under Sustained Load

**What goes wrong:** The Pi 5 throttles its CPU from 2.4GHz to 800MHz when it reaches ~85°C. Under sustained voice pipeline load (continuous STT + LLM + TTS), this can happen within 5-10 minutes without adequate cooling. Inference time doubles or triples under throttle.

**Prevention:**
- Use an active cooling solution (official Pi 5 active cooler or third-party heatsink+fan) in deployment
- Monitor temperature: `vcgencmd measure_temp` should stay below 75°C under load
- Run a sustained 15-minute benchmark on Pi before declaring performance acceptable
- Do not use Pi 5 in a sealed enclosure without ventilation

**Detection:** `vcgencmd measure_temp` returns >80°C. Inference time is variable (fast at start, slow after a few minutes). `dmesg` shows "CPU throttled" messages.

**Phase:** Phase 3 (Pi deployment validation). Hardware concern, but must be confirmed before shipping.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Pi environment setup | Moonshine ARM64 wheel unavailable (Pitfall 4) | Validate `pip install useful-moonshine` on Pi before any other work |
| Pi environment setup | Ollama model not pre-pulled (Pitfall 5) | Include `ollama pull qwen2.5:1.5b` in setup script with size verification |
| Pi environment setup | Piper voice model missing (Pitfall 6) | Bundle `.onnx` voice file in deployment package |
| Audio I/O implementation | Windows vs Linux device API differences (Pitfall 2) | Abstract audio behind a platform-neutral class immediately |
| STT integration | Sample rate mismatch (Pitfall 7) | Assert `samplerate=16000` at capture and Moonshine input |
| LLM integration on Pi | RAM exhaustion from all models loaded (Pitfall 1) | Measure `free -m` after each component loads; use Moonshine tiny |
| LLM integration on Pi | Ollama GPU config errors (Pitfall 10) | Explicitly set CPU-only mode, set thread count to 4 |
| TTS integration | Piper subprocess overhead (Pitfall 8) | Use `piper-tts` Python bindings or persistent subprocess |
| Full pipeline | Blocking architecture, 15s+ latency (Pitfall 3) | Use `stream_ask()` + sentence-level TTS from the start |
| Full pipeline | Empty transcription passed to LLM (Pitfall 9) | Add guard validation at every stage boundary |
| Full pipeline | Markdown in LLM output (Pitfall 12) | Add `clean_for_speech()` before Piper; update system prompt |
| Full pipeline | VAD false triggers from noise (Pitfall 13) | Test in real noise conditions; prefer push-to-talk for v1 |
| Pi deployment | Thermal throttling (Pitfall 15) | Active cooling, 15-min burn-in test before sign-off |
| Pi deployment | Cross-platform path issues (Pitfall 11) | Config-driven platform selection for all binary paths |

---

## Most Important Single Action

**Before writing a single line of Moonshine, audio, or Piper code: SSH into the Pi and run:**

```bash
pip install useful-moonshine onnxruntime
free -m  # after install, before anything else
```

If either command fails, the entire architecture needs to be reconsidered. All other pitfalls are manageable; this one is a potential blocker.

---

## Sources and Confidence Notes

| Claim | Confidence | Basis |
|-------|------------|-------|
| Moonshine memory footprint estimates | MEDIUM | Training knowledge of ONNX STT models at this parameter count; verify on Pi |
| qwen2.5:1.5b Ollama RAM usage ~900MB-1.1GB | MEDIUM | Training knowledge of GGUF quantization at this scale; verify with `ollama ps` |
| Piper voice model sizes 60-130MB | MEDIUM | Training knowledge; verify by downloading target voice before committing |
| ARM64 wheel availability for Moonshine | LOW | Cannot verify without web access; must be tested on Pi directly |
| Pi 5 thermal throttle at 85°C | MEDIUM | Well-documented Pi 5 behavior; verify with `vcgencmd` in testing |
| Ollama `OLLAMA_NUM_THREADS=4` for Pi 5 | MEDIUM | Pi 5 has 4 cores (Cortex-A76); standard Ollama tuning practice |
| Piper `piper-tts` PyPI bindings available | LOW | Cannot verify without web access; confirm before planning TTS integration |
| Sample rate 16000Hz for Moonshine | HIGH | Moonshine is documented as processing 16kHz audio (standard for STT models) |

**Note:** Web search and WebFetch were unavailable during this research session. All LOW confidence items must be validated with direct testing on Pi hardware or verified via current documentation before implementation begins.
