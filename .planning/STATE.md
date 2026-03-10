# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.
**Current focus:** Phase 2 - STT Integration

## Current Position

Phase: 2 of 4 (STT Integration) — IN PROGRESS
Plan: 1 of 1 in Phase 2 (02-01 complete)
Status: Phase 2 Plan 1 complete — Moonshine STT module built and tested
Last activity: 2026-03-10 — Phase 2 Plan 1 complete (stt.py, 5 offline tests, 12/12 passing)

Progress: [███░░░░░░░] 37%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: ~45 min/plan
- Total execution time: ~2h 15m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-audio-foundation | 2/2 | ~120 min | ~60 min |
| 02-stt-integration | 1/1 | ~15 min | ~15 min |

**Recent Trend:**
- Last 5 plans: 01-01 (~60 min), 01-02 (~60 min), 02-01 (~15 min)
- Trend: On pace

*Updated after each plan completion*
| Phase 01-audio-foundation P02 | 60 | 3 tasks | 3 files |
| Phase 02-stt-integration P01 | 15 | 2 tasks | 3 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware before STT code is written — run `pip install moonshine-voice` on actual Pi first
- [Phase 1 risk]: RAM headroom is estimated at ~534MB; measure `free -m` after each component loads on physical Pi — switch to Moonshine tiny-en if headroom drops below 200MB
- [Phase 3 risk]: End-to-end latency target of <10s is tight; LLM alone takes 3-8s on Pi 5 — profile each stage separately before declaring target achievable

## Session Continuity

Last session: 2026-03-10
Stopped at: Completed 02-stt-integration 02-01-PLAN.md — Moonshine STT module complete
Resume file: None
