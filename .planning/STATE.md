# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.
**Current focus:** Phase 3 - TTS Pipeline and Display

## Current Position

Phase: 3 of 4 (TTS Pipeline and Display) — IN PROGRESS
Plan: 1 of 2 in Phase 3 (03-01 complete)
Status: Phase 3 Plan 1 complete — Piper TTS module built and tested (learnbox/tts.py, 6 offline tests, 18/18 passing)
Last activity: 2026-03-24 — Phase 3 Plan 1 complete (tts.py, 6 offline tests, 18/18 passing)

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: ~40 min/plan
- Total execution time: ~2h 40m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-audio-foundation | 2/2 | ~120 min | ~60 min |
| 02-stt-integration | 1/1 | ~15 min | ~15 min |
| 03-tts-pipeline-and-display | 1/2 | ~25 min | ~25 min |

**Recent Trend:**
- Last 5 plans: 01-01 (~60 min), 01-02 (~60 min), 02-01 (~15 min), 03-01 (~25 min)
- Trend: On pace

*Updated after each plan completion*
| Phase 01-audio-foundation P02 | 60 | 3 tasks | 3 files |
| Phase 02-stt-integration P01 | 15 | 2 tasks | 3 files |
| Phase 03-tts-pipeline-and-display P01 | 25 | 2 tasks | 5 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware before STT code is written — run `pip install moonshine-voice` on actual Pi first
- [Phase 1 risk]: RAM headroom is estimated at ~534MB; measure `free -m` after each component loads on physical Pi — switch to Moonshine tiny-en if headroom drops below 200MB
- [Phase 3 risk]: End-to-end latency target of <10s is tight; LLM alone takes 3-8s on Pi 5 — profile each stage separately before declaring target achievable
- [Phase 3 note]: espeak-ng embedded in piper-tts pip package works on Windows; validate on Pi OS Bookworm in Phase 4 — may need `sudo apt-get install espeak-ng` if phonemization errors occur

## Session Continuity

Last session: 2026-03-24
Stopped at: Completed 03-tts-pipeline-and-display 03-01-PLAN.md — Piper TTS module complete
Resume file: None
