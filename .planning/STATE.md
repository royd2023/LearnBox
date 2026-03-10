# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.
**Current focus:** Phase 2 - STT Integration

## Current Position

Phase: 1 of 4 (Audio Foundation) — COMPLETE; next: Phase 2 STT Integration
Plan: 2 of 2 in Phase 1 (all complete)
Status: Phase 1 complete — ready to plan Phase 2
Last activity: 2026-03-10 — Phase 1 Audio Foundation complete (2/2 plans done, human round-trip verified)

Progress: [██░░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: ~60 min/plan
- Total execution time: ~2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-audio-foundation | 2/2 | ~120 min | ~60 min |

**Recent Trend:**
- Last 5 plans: 01-01 (~60 min), 01-02 (~60 min)
- Trend: On pace

*Updated after each plan completion*
| Phase 01-audio-foundation P02 | 60 | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-work]: qwen2.5:1.5b chosen over 0.5b — 0.5b had 2+ wrong answers in benchmark; 1.5b passed all 10
- [Pre-work]: Push-to-talk gating chosen over always-on wake word — zero RAM overhead, more reliable
- [Pre-work]: Sequential synchronous pipeline (no asyncio) — all blocking ops use C extensions that don't yield to event loop
- [Phase 01-audio-foundation]: sd.wait() mandatory after sd.play() to enforce blocking playback contract and prevent Phase 3 pipeline overlap
- [Phase 01-audio-foundation]: play_audio accepts int16 and float32 without conversion; sounddevice handles both natively

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware before STT code is written — run `pip install moonshine-voice` on actual Pi first
- [Phase 1 risk]: RAM headroom is estimated at ~534MB; measure `free -m` after each component loads on physical Pi — switch to Moonshine tiny-en if headroom drops below 200MB
- [Phase 3 risk]: End-to-end latency target of <10s is tight; LLM alone takes 3-8s on Pi 5 — profile each stage separately before declaring target achievable

## Session Continuity

Last session: 2026-03-10
Stopped at: Completed 01-audio-foundation 01-02-PLAN.md — Phase 1 Audio Foundation complete
Resume file: None
