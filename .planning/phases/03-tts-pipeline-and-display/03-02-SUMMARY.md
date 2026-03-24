---
phase: 03-tts-pipeline-and-display
plan: 02
subsystem: pipeline
tags: [main, pipeline, tts, stt, mic, llm, display, error-handling]

# Dependency graph
requires:
  - phase: 01-audio-foundation
    provides: record_until_silence, play_audio
  - phase: 02-stt-integration
    provides: transcribe()
  - plan: 03-01
    provides: speak, speak_error, play_thinking_cue
provides:
  - Complete end-to-end voice pipeline in main.py
  - All five display states: Listening..., You: ..., Thinking..., LearnBox: ..., Speaking...
  - play_thinking_cue before LLM call (TTS-02)
  - speak_error on LLM RuntimeError (PIPE-04)
  - speak(response) in isolated try/except (PIPE-04)
  - Both model imports at module level (PIPE-02)
affects: [end-user experience]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Module-level model imports (from learnbox import stt/tts) for startup preload
    - Isolated try/except for TTS call — TTS failure never kills the loop
    - speak_error() for LLM RuntimeError — spoken error + print fallback

key-files:
  modified:
    - main.py

key-decisions:
  - "from learnbox import tts (not from learnbox.tts import ...) — triggers PiperVoice.load at startup before first question"
  - "play_thinking_cue called AFTER transcript confirmed non-empty and BEFORE ask() — provides <500ms audio feedback"
  - "speak(response) in its own try/except — TTS crash is non-fatal, pipeline continues"
  - "speak_error used for LLM RuntimeError only — other errors use print()"

requirements-completed: [PIPE-01, PIPE-02, PIPE-03, PIPE-04, DISP-01, DISP-02]

# Metrics
duration: 10min
completed: 2026-03-24
---

# Phase 3 Plan 02: Complete Voice Pipeline Wiring Summary

**main.py wired with full Mic → STT → thinking cue → LLM → TTS → Speaker pipeline. Human verified end-to-end on Windows. 18/18 tests passing.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-03-24
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 1

## Accomplishments
- main.py implements complete Phase 3 pipeline: mic → stt → thinking_cue → llm → tts
- All five display states present and in correct order: Listening..., You: ..., Thinking..., LearnBox: ..., Speaking...
- play_thinking_cue() called after transcript confirmed, before ask() — audible within 500ms
- speak_error() called on LLM RuntimeError — spoken error with print fallback
- speak(response) in isolated try/except — TTS failure does not kill the loop
- Both model imports at module level: `from learnbox import stt` and `from learnbox import tts`
- Human verified: spoken question produces spoken answer end-to-end on Windows
- Human verified: mic does not re-open during TTS playback
- Full test suite 18/18 passing: 7 audio + 5 stt + 6 tts, no regressions

## Task Commits

1. **Task 1: Replace main.py with complete Phase 3 pipeline** - `dd49659` (feat)
2. **Task 2: Human verify full end-to-end voice pipeline** - Human confirmed ✓

## Files Modified
- `main.py` - Complete Phase 3 pipeline with all display states, thinking cue, TTS wiring, error handling

## Decisions Made
- Module-level `from learnbox import tts` (not direct function import) — ensures PiperVoice.load() executes at startup before first interaction
- TTS call wrapped in its own `try/except Exception` separate from LLM error handler — failure modes are independent

## Deviations from Plan

None. main.py already contained the complete Phase 3 implementation from commit `dd49659`. Human verification confirmed end-to-end pipeline works.

## Phase 3 Requirements Completed

- TTS-01: speak(response) synthesizes LLM response via Piper ✓
- TTS-02: play_thinking_cue() before LLM call, <500ms ✓
- TTS-03: strip_markdown inside speak() ✓
- TTS-04: "Speaking..." printed before TTS ✓
- PIPE-01: Full Mic → STT → LLM → TTS → Speaker loop ✓
- PIPE-02: All models loaded at startup via module imports ✓
- PIPE-03: Mic does not open during TTS (sd.wait() blocks) ✓
- PIPE-04: LLM error produces spoken error via speak_error() ✓
- DISP-01: "You: {transcript}" printed ✓
- DISP-02: "LearnBox: {response}" printed ✓

---
*Phase: 03-tts-pipeline-and-display*
*Completed: 2026-03-24*
