---
plan: 02-02
phase: 02-stt-integration
status: complete
---

# Summary: 02-02 — Voice Loop + Human Verification

## What Was Built

- `main.py` replaced text input loop with full push-to-talk voice pipeline
- KeyboardInterrupt caught during mic recording for clean Ctrl+C exit

## Key Files

### modified
- `main.py`

## Human Verification Results

- 12/12 tests pass (pytest tests/ -v)
- "What is photosynthesis?" transcribed accurately, LLM responded correctly
- Empty recording guard: loops with "(no speech detected — try again)"
- Ctrl+C exits cleanly with "Goodbye." (after fix)

## Decisions Made

- push-to-talk via `input()` (Enter to start) — no pynput/keyboard deps, works on Pi
- Two guards: empty audio from mic + empty transcript from Moonshine
- "Listening..." printed before mic opens, "Thinking..." before LLM call
- KeyboardInterrupt caught in main loop around record_until_silence() call

## Self-Check: PASSED

All verification confirmed by human on 2026-03-10.
