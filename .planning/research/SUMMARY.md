# Project Research Summary

**Project:** LearnBox — offline voice-first educational assistant
**Domain:** Edge voice pipeline (STT + LLM + TTS) on constrained hardware
**Researched:** 2026-03-10
**Confidence:** MEDIUM

## Executive Summary

LearnBox is a single-user, fully offline voice assistant targeting students aged 8-18 on Raspberry Pi 5 (2GB RAM). The LLM layer is already working (qwen2.5:1.5b via Ollama, `learnbox/llm.py`). The remaining work is adding Moonshine STT and Piper TTS to complete the voice pipeline. Research confirms this is technically feasible within the hardware constraints: estimated peak RAM usage is ~1514 MB against a 2048 MB ceiling, leaving ~534 MB headroom when using Moonshine base-en. Both Moonshine (moonshine-voice 0.0.49) and Piper (piper-tts 1.4.1) publish native ARM64 wheels for Pi OS Bookworm — no source builds required.

The recommended approach is a strictly sequential, synchronous pipeline: mic capture → Moonshine STT → Ollama LLM → Piper TTS → speaker playback. No asyncio, no streaming LLM-to-TTS chaining. All three model objects (Moonshine transcriber, Piper voice, and Ollama via its HTTP daemon) are initialized once at startup and reused across turns. A lightweight display thread consuming a `queue.Queue` allows screen rendering to overlap with TTS playback — the only parallelism needed. Push-to-talk (a button or key) gates mic capture, eliminating the need for an always-on wake-word model and its associated RAM and CPU overhead.

The key risks are hardware-specific and must be validated early. ARM64 wheel availability for Moonshine must be confirmed on an actual Pi before committing architecture. RAM headroom must be measured with `free -m` after each component loads — estimates from research have MEDIUM confidence and reality on the hardware may differ. The 10-second end-to-end latency target is tight: LLM inference alone takes 3-8 seconds on Pi 5, leaving 2-7 seconds for STT, TTS, and audio playback. A "thinking" audio cue immediately after transcription is non-optional UX. Thermal throttling under sustained load is a real hardware concern requiring an active cooling solution in deployment.

---

## Key Findings

### Recommended Stack

The voice pipeline adds three Python packages to an existing `httpx`-only stack: `moonshine-voice`, `piper-tts`, and `sounddevice`. All three have verified wheels for Windows x64 (development) and Linux aarch64 (Pi production). No system-level dependencies on Windows; `libportaudio2` is the only system package needed on Pi.

**Core technologies:**
- `moonshine-voice 0.0.49` (STT) — Moonshine base-en model, 16kHz push-to-talk transcription; 25x faster than Whisper Tiny on Pi 5 (237ms vs 5,863ms); single pip install with no separate ONNX management
- `piper-tts 1.4.1` (TTS) — ONNX-based neural TTS; `en_US-lessac-medium` voice (~60 MB); fully offline, no cloud dependency; maintained by OHF-Voice (Home Assistant foundation)
- `sounddevice 0.5.5` (audio I/O) — PortAudio bindings for both mic capture and speaker playback; shared dependency with Moonshine; bundles PortAudio DLLs on Windows, uses system ALSA on Pi
- `httpx 0.28.1` (LLM client) — already present; synchronous wrapper around Ollama HTTP API
- `numpy` (explicit pin) — indirect dep of moonshine-voice and sounddevice; pin explicitly to avoid install conflicts

**Critical version note:** Use Python 3.11 for both platforms. Pi OS Bookworm ships Python 3.11 by default. onnxruntime 1.24.x (pulled by piper-tts) dropped Python 3.9 support — 3.11 is the safe choice for all components.

**Models to pre-download (not bundled in wheels):**
- Moonshine base-en: ~134 MB, downloaded via `python -m moonshine_voice.download --language en`
- Piper en_US-lessac-medium: ~60 MB, downloaded via `python -m piper.download_voices en_US-lessac-medium`

Both must be downloaded with internet access before offline deployment. See STACK.md for full installation commands for both platforms.

### Expected Features

The pipeline is currently text-in, text-out. The milestone scope is completing it to voice-in, voice-out.

**Must have (this milestone):**
- Push-to-talk trigger (key/button) — simpler and more reliable than wake-word; zero RAM overhead
- Microphone audio capture at 16kHz mono — required format for Moonshine
- Moonshine STT transcription — converts captured audio to text
- Ollama LLM response — already done; wire it in
- Piper TTS synthesis — converts LLM text response to audio
- Speaker playback via sounddevice — plays synthesized audio
- Screen text display (question + answer + "Thinking..." state) — PROJECT.md requirement
- Spoken + visual error handling — "I didn't catch that" for empty transcriptions; no silent failure
- End-to-end latency within ~10s on Pi 5 — must be profiled on actual hardware

**Should have (low complexity, high student value):**
- Audio replay of last answer — buffer Piper output; press a button to hear again
- Session question history on screen — in-memory list; no database needed

**Defer to post-milestone:**
- Wake-word detection — complexity/RAM cost not justified until push-to-talk is validated
- Age-adaptive explanation style — system prompt experiment, not pipeline work
- Teacher topic lock — requires configuration UI layer
- Autostart/boot-to-ready (systemd) — deployment hardening; separate milestone
- Multilingual STT — Moonshine is English-only at current version; blocked

**Anti-features (never build in v1):**
- Always-on wake-word model (50-100MB RAM, continuous CPU, high false-trigger rate in classrooms)
- User profiles or cross-session persistence (no database, no privacy surface)
- Streaming LLM-to-TTS (choppy audio; full response synthesis is fast enough at 2-3 sentences)
- Web/API exposure (adds Flask/FastAPI; this is a physical device, not a browser app)
- Internet fallback (contradicts the core offline value proposition)

### Architecture Approach

The pipeline is sequential and synchronous per turn — each stage's output is the next stage's input, so no within-turn parallelism is possible or beneficial. The recommended structure is one main thread running `record() → transcribe() → ask() → synthesize() → play()`, with an optional daemon display thread consuming a `queue.Queue` so screen updates happen concurrently with TTS playback. Do not introduce asyncio: all blocking operations (audio I/O, Moonshine inference, Piper synthesis) use C extensions that do not yield to an event loop, requiring `run_in_executor` wrappers everywhere with no throughput benefit. The existing synchronous `httpx` client in `llm.py` reinforces this choice.

**Major components (target file structure):**
1. `learnbox/mic.py` — audio capture; sounddevice.InputStream at 16kHz mono int16; energy-based VAD for silence detection; never hardcode device index
2. `learnbox/stt.py` — Moonshine transcription; load model once at startup via `get_model_for_language("en")`; guard against empty transcript before returning
3. `learnbox/llm.py` — already complete; synchronous httpx wrapper around Ollama; `ask()` with 120s timeout
4. `learnbox/tts.py` — Piper synthesis via Python binding (`PiperVoice.load()` once at startup); yields int16 audio chunks
5. `learnbox/audio.py` — speaker playback; `sd.play()` + `sd.wait()` for blocking playback; buffers last output for replay feature
6. `learnbox/pipeline.py` — orchestrates one full turn; owns model references; gates on empty transcript; puts `(transcript, response)` into display queue after LLM returns
7. `learnbox/display.py` — optional daemon thread; renders question + answer to screen; uses framebuffer not full X11
8. `main.py` — entry point; run loop; push-to-talk event → `pipeline.run_turn()`

**Build order (testable in isolation at each stage):**
Stage 1: Audio capture → Stage 2: STT → Stage 3: TTS + playback (LLM not needed here) → Stage 4: Full pipeline wiring → Stage 5: Robustness + error handling → Stage 6: Display thread → Stage 7: Pi 5 validation (RAM, latency, thermal)

### Critical Pitfalls

1. **RAM exhaustion with all three models loaded** — Estimated combined usage is ~1514 MB; measure with `free -m` after each component loads on the actual Pi before declaring the architecture safe. Start with Moonshine base-en; switch to tiny if headroom is tight. Set `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1`.

2. **Moonshine ARM64 wheel unavailability on Pi** — The PITFALLS.md flags this as potentially a full architectural blocker (LOW confidence). Before writing any STT code, SSH into the Pi and run `pip install moonshine-voice` to confirm it resolves. Note: STACK.md (verified from PyPI) confirms `manylinux_2_31_aarch64` and `manylinux_2_34_aarch64` wheels exist; this risk is likely mitigated but must be confirmed.

3. **Perceived latency from blocking silence** — LLM alone takes 3-8s on Pi 5. Without an immediate audio acknowledgment ("one moment...") after STT completes, the device appears frozen to students. This is a UX-critical pattern, not a nice-to-have. Play a short cue within 500ms of transcription completing.

4. **Model assets not pre-installed in offline deployment** — `ollama pull qwen2.5:1.5b` and Piper voice model download both require internet. In an offline deployment, these must be pre-pulled during Pi setup or bundled in the deployment image. Include startup verification: check that model files exist before accepting voice input.

5. **LLM response markdown breaks TTS output** — qwen2.5 occasionally returns markdown (`**bold**`, `- bullets`). Piper reads these as literal text ("asterisk asterisk bold asterisk asterisk"). Add a `clean_for_speech()` preprocessing step before TTS and update the system prompt to explicitly forbid markdown formatting.

---

## Implications for Roadmap

Based on the dependency chain and the hardware validation risk, a 4-phase structure is recommended.

### Phase 1: Pi Environment and Hardware Validation

**Rationale:** All other work depends on the Pi hardware working. ARM64 wheel availability (Pitfall 4), RAM headroom (Pitfall 1), and Ollama model pre-pull (Pitfall 5) are all blockers that, if unresolved, require architectural changes. Discovering them in Phase 1 is cheap; discovering them in Phase 3 is a rewrite. This phase is also the platform abstraction foundation — audio device handling and path management must be cross-platform from the first line of code.

**Delivers:** Confirmed Pi install of all dependencies; measured RAM baseline; Ollama running and model verified; Piper voice and Moonshine model files present; platform-neutral audio device abstraction (`mic.py` skeleton).

**Addresses:** Push-to-talk gating architecture decision; cross-platform path/binary abstraction (Pitfall 11); Ollama CPU-only config on Pi (Pitfall 10).

**Avoids:** Building on an unvalidated foundation; late discovery of ARM64 incompatibilities.

**Research flag:** This phase is well-documented via STACK.md installation commands. Standard patterns apply. No additional phase research needed.

---

### Phase 2: Audio Capture and STT Integration

**Rationale:** The pipeline's input end must be validated in isolation before wiring the rest. A bad audio capture (wrong sample rate, wrong device, wrong format) produces silent failures in Moonshine that look like transcription bugs. Isolating audio capture and confirming it produces 16kHz mono int16 PCM before touching STT eliminates a major ambiguity class.

**Delivers:** `learnbox/mic.py` with energy-based VAD silence detection; `learnbox/stt.py` with Moonshine transcription; integration test: speak into mic, print transcript.

**Uses:** `moonshine-voice 0.0.49`, `sounddevice 0.5.5`, `numpy`.

**Implements:** Audio Capture and STT components from Architecture.

**Avoids:** Sample rate mismatch garbage transcriptions (Pitfall 7); hardcoded device indices (Pitfall 2); passing empty transcription to LLM (Pitfall 9 — add guard here).

**Research flag:** STACK.md provides the exact Moonshine Python API pattern. Standard patterns. No additional research needed.

---

### Phase 3: TTS Integration and Full Pipeline Wiring

**Rationale:** TTS must be validated alone (input: hardcoded string → output: audible speech) before connecting it to the pipeline. Once both ends are confirmed working, Stage 4 pipeline wiring is connecting known-good components. The "thinking" audio cue and the `clean_for_speech()` preprocessing step belong in this phase because they are part of the LLM-to-TTS boundary.

**Delivers:** `learnbox/tts.py` and `learnbox/audio.py`; `learnbox/pipeline.py` wiring full turn; `clean_for_speech()` markdown stripper; "thinking" audio cue on STT completion; full end-to-end voice turn working on both Windows and Pi.

**Uses:** `piper-tts 1.4.1`, existing `learnbox/llm.py`.

**Implements:** TTS, Audio Playback, and Pipeline Orchestrator components from Architecture.

**Avoids:** Piper subprocess overhead per utterance (use Python binding, load once at startup — Pitfall 8); streaming LLM into TTS (anti-pattern — buffer full response); markdown in TTS output (Pitfall 12).

**Research flag:** Piper Python binding (`PiperVoice`) API is documented in STACK.md. Standard patterns. No additional research needed.

---

### Phase 4: Pi Validation, Hardening, and Display

**Rationale:** End-to-end latency and RAM headroom can only be accurately measured on Pi hardware under sustained load. Thermal throttling becomes visible only after 5-10 minutes of continuous use. These cannot be caught in development on Windows. Display rendering (framebuffer vs X11) is a Pi-specific decision. This phase also adds the low-complexity high-value features (audio replay, session history) that improve student experience without blocking the core pipeline.

**Delivers:** Measured end-to-end latency on Pi (must be <10s); confirmed RAM headroom; thermal stress test (15-minute burn-in); `learnbox/display.py` with framebuffer rendering; audio replay of last answer; session question history on screen; spoken + visual error handling for all failure modes; active cooling recommendation for deployment.

**Implements:** Display component from Architecture; robustness and error recovery layer.

**Avoids:** Thermal throttling degradation (Pitfall 15); X11 desktop consuming 200-400MB RAM (use Pi OS Lite + framebuffer — Architecture anti-pattern 5); OOM from RAM over-allocation (validate measurements from Phase 1 against Phase 3 reality).

**Research flag:** Framebuffer rendering approach (pygame in framebuffer mode vs direct write) may need a quick research pass if the team is unfamiliar with headless Pi display. Otherwise standard patterns.

---

### Phase Ordering Rationale

- **Pi-first validation** is Phase 1 (not last) because the ARM64 wheel risk and RAM constraint are architectural-level blockers. Discovering them late invalidates prior implementation work.
- **Audio before STT** (both in Phase 2) enforces the ARCHITECTURE.md build order: confirm raw capture works before adding inference.
- **TTS tested alone before pipeline wiring** (Phase 3) eliminates ambiguity when debugging the full pipeline — you know mic, STT, and TTS each work independently.
- **Display and hardening last** (Phase 4) follows from the dependency graph: display reads from the pipeline queue, so the pipeline must exist and be stable first.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (display):** If framebuffer rendering approach is unfamiliar, a quick research pass on pygame framebuffer mode or direct fb0 write patterns is warranted. The Pi OS Lite + headless display setup has some Pi-specific nuances.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Installation commands fully documented in STACK.md; confirmed Pi OS Bookworm compatibility.
- **Phase 2:** Moonshine Python API and sounddevice patterns fully documented in STACK.md and ARCHITECTURE.md.
- **Phase 3:** Piper `PiperVoice` Python API documented in STACK.md; pipeline wiring follows established sequential pattern from ARCHITECTURE.md.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | STACK.md verified against PyPI, official GitHub docs, and Ollama registry. ARM64 wheel availability confirmed from PyPI metadata. Exact versions pinned. |
| Features | MEDIUM | Table stakes and anti-features grounded in hardware constraints and PROJECT.md (HIGH). UX patterns for ages 8-18 from training data synthesis (MEDIUM). No user studies cited. |
| Architecture | MEDIUM | Sequential pipeline model is logically sound and confirmed by learnbox/llm.py code inspection (HIGH). Moonshine/Piper API specifics from training data (MEDIUM-LOW) — STACK.md's verified API patterns supersede ARCHITECTURE.md's LOW-confidence guesses where they conflict. |
| Pitfalls | MEDIUM | Pitfalls grounded in Pi hardware constraints (thermal, RAM) and cross-platform deployment patterns (MEDIUM). ARM64 wheel availability flagged LOW by PITFALLS.md but partially resolved by STACK.md's PyPI verification. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **ARM64 wheel validation on physical Pi hardware** — STACK.md confirms wheels exist on PyPI; PITFALLS.md correctly flags that confirmation on actual Pi hardware is still required. Run `pip install moonshine-voice piper-tts sounddevice` on a fresh Pi OS Bookworm image at the start of Phase 1. Do not proceed with STT/TTS code until this passes.

- **RAM headroom measurement on actual hardware** — STACK.md gives ~534 MB estimated headroom using base-en; ARCHITECTURE.md estimates are less precise. Actual figures depend on ONNX Runtime version and Python process overhead. Measure `free -m` after each component loads during Phase 1 and 2. If headroom drops below 200 MB, switch to Moonshine tiny-en to recover ~80 MB.

- **End-to-end latency on Pi 5** — The 10-second target is well-established in PROJECT.md but unvalidated against actual Pi 5 performance. PITFALLS.md notes LLM alone takes 3-8s. The remaining budget for STT + TTS + audio is tight. Profile each stage separately during Phase 2/3 before declaring the target achievable.

- **Ollama GPU/CPU config on Pi 5** — PITFALLS.md recommends `OLLAMA_NUM_THREADS=4` and disabling GPU offloading on Pi 5. These are MEDIUM confidence. Validate with `ollama ps` and monitor inference time during Phase 1 Ollama setup.

- **Moonshine API surface** — ARCHITECTURE.md's Moonshine usage pattern is LOW confidence (training data). STACK.md's `MicTranscriber` / `TranscriptEventListener` API is verified from the official GitHub README. Use STACK.md's patterns for implementation. ARCHITECTURE.md's low-confidence guesses should not be used for coding.

---

## Sources

### Primary (HIGH confidence)
- `moonshine-voice` PyPI (v0.0.49, 2026-02-23) — wheel availability, Python API, Pi 5 benchmarks
- Moonshine GitHub README (official) — `MicTranscriber`, `get_model_for_language`, Pi 5 latency benchmarks (237ms Tiny)
- `piper-tts` PyPI (v1.4.1, 2026-02-05) — wheel availability, Python API, `PiperVoice.load()`
- Piper API Python docs (OHF-Voice/piper1-gpl) — `synthesize()` generator pattern, AudioChunk format
- `sounddevice` PyPI and official docs — PortAudio bundling on Windows, ALSA on Pi
- Ollama GitHub releases (v0.17.7, 2026-03-05) — confirmed Pi support
- qwen2.5:1.5b Ollama registry manifest — 940 MB model size confirmed
- `learnbox/llm.py` direct code inspection — synchronous httpx, stream=False default, ConnectError handling

### Secondary (MEDIUM confidence)
- Training data synthesis: child-computer interaction latency tolerance patterns
- Training data: Pi 5 thermal throttle behavior under sustained CPU load
- Training data: Ollama qwen2.5:1.5b RAM footprint (~900MB-1.1GB range)
- Training data: Pi OS Lite vs desktop RAM savings (~200-400MB)
- Training data: energy-based VAD silence detection patterns

### Tertiary (LOW confidence — validate before implementation)
- ARM64 wheel compatibility for moonshine-voice on Pi OS Bookworm (must test on physical hardware)
- Moonshine Python API surface in ARCHITECTURE.md (superseded by STACK.md's verified patterns)
- Piper subprocess integration details in ARCHITECTURE.md (use Python binding per STACK.md instead)
- `OLLAMA_FLASH_ATTENTION=0` stability effect on Pi 5 (verify on hardware)

---
*Research completed: 2026-03-10*
*Ready for roadmap: yes*
