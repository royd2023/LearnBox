# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.
**Current focus:** Phase 4 - Pi Deployment and Integration Testing

## Current Position

Phase: 3 of 4 (TTS Pipeline and Display) — COMPLETE
Plan: 2 of 2 in Phase 3 (03-02 complete)
Status: Phase 3 complete — full voice pipeline working end-to-end. Student speaks, hears spoken answer. 18/18 tests passing.
Last activity: 2026-03-24 — Phase 3 Plan 2 complete (main.py wired, human-verified end-to-end on Windows)

Progress: [███████░░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: ~35 min/plan
- Total execution time: ~2h 50m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-audio-foundation | 2/2 | ~120 min | ~60 min |
| 02-stt-integration | 1/1 | ~15 min | ~15 min |
| 03-tts-pipeline-and-display | 2/2 | ~35 min | ~17 min |

**Recent Trend:**
- Last 5 plans: 01-01 (~60 min), 01-02 (~60 min), 02-01 (~15 min), 03-01 (~25 min), 03-02 (~10 min)
- Trend: Accelerating

*Updated after each plan completion*
| Phase 01-audio-foundation P02 | 60 | 3 tasks | 3 files |
| Phase 02-stt-integration P01 | 15 | 2 tasks | 3 files |
| Phase 03-tts-pipeline-and-display P01 | 25 | 2 tasks | 5 files |
| Phase 03-tts-pipeline-and-display P02 | 10 | 2 tasks | 1 file |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-work]: qwen2.5:1.5b chosen over 0.5b — 0.5b had 2+ wrong answers in benchmark; 1.5b passed all 10
- [Pre-work]: Push-to-talk gating chosen over always-on wake word — zero RAM overhead, more reliable
- [Pre-work]: Sequential synchronous pipeline (no asyncio) — all blocking ops use C extensions that don't yield to event loop
- [Phase 01-audio-foundation]: sd.wait() mandatory after sd.play() to enforce blocking playback contract and prevent Phase 3 pipeline overlap
- [Phase 01-audio-foundation]: play_audio accepts int16 and float32 without conversion; sounddevice handles both natively
- [Phase 02-stt-integration]: Transcriber initialized at module level — model load cost paid once at import, not per transcribe() call
- [Phase 02-stt-integration]: int16->float32 conversion (/ 32768.0) belongs in stt.py, not mic.py — mic.py stays dtype-agnostic per its design contract
- [Phase 02-stt-integration]: FakeTranscriber monkeypatching pattern established for offline STT tests — patches _transcriber instance, not the class
- [Phase 03-tts-pipeline-and-display]: piper-tts>=1.4.1 pinned — only pip-installable Piper with ARM64 wheels; embeds espeak-ng (no apt install on Windows)
- [Phase 03-tts-pipeline-and-display]: Model-file existence check before piper.voice import — gives informative RuntimeError with download command
- [Phase 03-tts-pipeline-and-display]: Monkeypatch target is learnbox.tts.play_audio (import binding), not learnbox.audio.play_audio
- [Phase 03-tts-pipeline-and-display]: speak_error() catches all Exception and falls back to print() — TTS failure must never crash the pipeline
- [Phase 03-tts-pipeline-and-display]: from learnbox import tts at module level in main.py — triggers PiperVoice.load at startup before first question
- [Phase 03-tts-pipeline-and-display]: speak(response) in isolated try/except separate from LLM error handler — TTS and LLM failure modes are independent

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware before STT code is written — run `pip install moonshine-voice` on actual Pi first
- [Phase 1 risk]: RAM headroom is estimated at ~534MB; measure `free -m` after each component loads on physical Pi — switch to Moonshine tiny-en if headroom drops below 200MB
- [Phase 3 risk]: End-to-end latency target of <10s is tight; LLM alone takes 3-8s on Pi 5 — profile each stage separately before declaring target achievable
- [Phase 3 note]: espeak-ng embedded in piper-tts pip package works on Windows; validate on Pi OS Bookworm in Phase 4 — may need `sudo apt-get install espeak-ng` if phonemization errors occur

## Session Continuity

Last session: 2026-03-24
Stopped at: Completed Phase 3 (03-tts-pipeline-and-display) — full voice pipeline human-verified end-to-end on Windows
Resume file: None
