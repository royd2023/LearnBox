# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-10)

**Core value:** A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.
**Current focus:** Phase 1 - Audio Foundation

## Current Position

Phase: 1 of 4 (Audio Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-10 — Roadmap created; all 22 v1 requirements mapped to 4 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-work]: qwen2.5:1.5b chosen over 0.5b — 0.5b had 2+ wrong answers in benchmark; 1.5b passed all 10
- [Pre-work]: Push-to-talk gating chosen over always-on wake word — zero RAM overhead, more reliable
- [Pre-work]: Sequential synchronous pipeline (no asyncio) — all blocking ops use C extensions that don't yield to event loop

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 risk]: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware before STT code is written — run `pip install moonshine-voice` on actual Pi first
- [Phase 1 risk]: RAM headroom is estimated at ~534MB; measure `free -m` after each component loads on physical Pi — switch to Moonshine tiny-en if headroom drops below 200MB
- [Phase 3 risk]: End-to-end latency target of <10s is tight; LLM alone takes 3-8s on Pi 5 — profile each stage separately before declaring target achievable

## Session Continuity

Last session: 2026-03-10
Stopped at: Roadmap created; ready to plan Phase 1
Resume file: None
