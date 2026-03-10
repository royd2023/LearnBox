---
phase: 01-audio-foundation
plan: 02
subsystem: audio
tags: [sounddevice, numpy, pytest, audio-playback, mic-capture, vad]

# Dependency graph
requires:
  - phase: 01-audio-foundation/01-01
    provides: learnbox/mic.py with energy-based VAD mic capture at 16kHz mono int16

provides:
  - learnbox/audio.py with blocking play_audio() via sd.play + sd.wait
  - tests/test_audio_foundation.py with 7 automated tests covering mic and audio modules
  - Human-verified audio round-trip confirming mic capture and speaker playback on Windows

affects:
  - Phase 2 STT Integration (imports play_audio for feedback cues)
  - Phase 3 TTS Pipeline (play_audio is the speaker output function)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - sd.play(audio, samplerate=sample_rate) followed immediately by sd.wait() for blocking playback
    - No device= ever passed to sounddevice — system default always used
    - Offline-safe unit tests using FakeStream context manager to mock InputStream without real hardware

key-files:
  created:
    - learnbox/audio.py
    - tests/test_audio_foundation.py
    - tests/__init__.py
  modified: []

key-decisions:
  - "sd.wait() is mandatory after sd.play() — without it, function returns before audio finishes, causing pipeline overlap in Phase 3"
  - "play_audio accepts both int16 and float32 without forcing conversion — sounddevice handles both natively"
  - "No last_audio buffer or replay feature in audio.py — that belongs in Phase 3 pipeline.py"

patterns-established:
  - "Blocking playback pattern: sd.play(audio, samplerate=rate) + sd.wait() — never omit sd.wait()"
  - "FakeStream mock pattern: context manager with read() method yielding controlled chunks for offline testing of sounddevice-dependent code"

requirements-completed: [AUD-03, AUD-04]

# Metrics
duration: ~60min (multi-session including human checkpoint)
completed: 2026-03-10
---

# Phase 1 Plan 02: Audio Playback + Automated Tests Summary

**Blocking speaker playback via sounddevice sd.play+sd.wait, 7-test automated suite covering mic and audio modules, and human-verified round-trip confirming mic captures voice and speaker plays it back on Windows**

## Performance

- **Duration:** ~60 min (including human checkpoint wait)
- **Started:** 2026-03-10
- **Completed:** 2026-03-10
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 3 created (learnbox/audio.py, tests/test_audio_foundation.py, tests/__init__.py)

## Accomplishments
- Implemented learnbox/audio.py with play_audio() — blocks until playback completes via sd.wait(), no hardcoded device index, accepts int16 and float32
- Created tests/test_audio_foundation.py with 7 tests across TestMicModule and TestAudioModule — fully offline-safe using FakeStream mock, all 7 pass
- Human confirmed end-to-end audio round-trip: mic captured 2.3s of voice, playback heard through speakers, 7/7 tests green — Phase 1 audio foundation complete

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement learnbox/audio.py** - `f1c2b8f` (feat)
2. **Task 2: Write automated tests** - `8513fb1` (feat)
3. **Task 3: Human round-trip verification** - APPROVED (no code commit — human gate)

## Files Created/Modified
- `learnbox/audio.py` - Blocking speaker playback using sounddevice; play_audio(audio, sample_rate) with sd.wait() enforcing blocking contract
- `tests/test_audio_foundation.py` - 7 automated tests: 4 for mic module (sample rate, record returns int16, silence-only, no hardcoded device) and 3 for audio module (sd.play+sd.wait called, no device=, float32 accepted)
- `tests/__init__.py` - Empty init to make tests a package

## Decisions Made
- sd.wait() after sd.play() is non-negotiable — without it, the function returns before audio finishes, causing pipeline overlap bugs when Phase 3 fires TTS while LLM is still streaming
- play_audio accepts both int16 and float32 without conversion — sounddevice handles both formats natively; forcing a conversion before calling would be unnecessary and lossy
- No last_audio buffer or replay feature added to audio.py — that belongs in Phase 3 pipeline.py where replay context makes sense

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 1 Audio Foundation is fully complete:
- learnbox/mic.py — 16kHz mono int16 mic capture with energy-based VAD (from 01-01)
- learnbox/audio.py — blocking speaker playback (from 01-02)
- tests/test_audio_foundation.py — 7 automated tests, all passing
- Human-verified on Windows: mic captures voice, speaker plays it back

Phase 2 (STT Integration) can begin. The audio layer is the stable foundation it depends on.

Blocker to note before Phase 2 STT code is written: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware first — run `pip install moonshine-voice` on the actual Pi before writing STT code.

## Self-Check: PASSED

- FOUND: .planning/phases/01-audio-foundation/01-02-SUMMARY.md
- FOUND: commit f1c2b8f (feat: implement blocking speaker playback in learnbox/audio.py)
- FOUND: commit 8513fb1 (feat: add automated tests for mic and audio foundation modules)

---
*Phase: 01-audio-foundation*
*Completed: 2026-03-10*
