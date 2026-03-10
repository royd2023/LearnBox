---
phase: 02-stt-integration
plan: 01
subsystem: stt
tags: [moonshine-voice, speech-to-text, numpy, int16, float32, offline]

# Dependency graph
requires:
  - phase: 01-audio-foundation
    provides: mic.py record_until_silence() returning int16 numpy array at 16kHz
provides:
  - learnbox/stt.py with transcribe(audio_int16) -> str
  - Moonshine Transcriber loaded at module level (single initialization)
  - int16-to-float32 conversion contract (/ 32768.0)
  - 5 offline-safe unit tests for stt.py
affects: [03-tts-integration, 04-pipeline-assembly]

# Tech tracking
tech-stack:
  added: [moonshine-voice>=0.0.49]
  patterns:
    - Module-level Transcriber initialization (load once, reuse per process)
    - Listener-based streaming transcription via TranscriptEventListener
    - int16->float32 normalization at STT boundary (not at mic layer)

key-files:
  created:
    - learnbox/stt.py
    - tests/test_stt.py
  modified:
    - requirements.txt

key-decisions:
  - "Transcriber instantiated at module level — model load cost (~200-500ms) paid once at import, not per transcribe() call"
  - "int16->float32 conversion done in stt.py using /32768.0 — mic.py intentionally returns raw int16 per its design contract"
  - "FakeTranscriber monkeypatching pattern established for offline STT tests — patches module-level _transcriber instance, not the class"

patterns-established:
  - "Pattern 1: STT boundary conversion — audio_float32 = audio_int16.astype(np.float32) / 32768.0"
  - "Pattern 2: Listener cleanup in finally block — _transcriber.remove_listener(listener) always runs even if add_audio raises"
  - "Pattern 3: Empty-audio early return — len(audio_int16) == 0 returns '' before any model access"

requirements-completed: [STT-01, STT-02]

# Metrics
duration: 15min
completed: 2026-03-10
---

# Phase 2 Plan 01: Moonshine STT Module Summary

**Moonshine base-en streaming transcription module with module-level Transcriber, int16->float32 conversion, and 5 offline-safe pytest tests using FakeTranscriber monkeypatching**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-10T22:15:36Z
- **Completed:** 2026-03-10T22:17:36Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created learnbox/stt.py with Moonshine Transcriber initialized at module level using get_model_for_language("en")
- transcribe() function converts int16 to float32 via /32768.0 and streams chunks to Moonshine via add_audio()
- 5 offline-safe tests in tests/test_stt.py using FakeTranscriber to replace the module-level _transcriber — no model download or hardware required for test runs
- Full test suite 12/12 passing with no regressions to Phase 1 audio tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Add moonshine-voice to requirements.txt and create learnbox/stt.py** - `7f0a60c` (feat)
2. **Task 2: Write offline-safe tests for stt.py** - `2d6c813` (test)

**Plan metadata:** *(docs commit follows)*

## Files Created/Modified

- `learnbox/stt.py` - Moonshine STT module: module-level Transcriber, _LineCollector listener, transcribe() with int16->float32 conversion
- `tests/test_stt.py` - 5 offline-safe pytest tests using FakeTranscriber monkeypatching
- `requirements.txt` - Added moonshine-voice>=0.0.49

## Decisions Made

- Transcriber initialized at module level: model load is slow (~200-500ms on Pi 5), paying that cost once at import avoids latency spikes per utterance
- int16->float32 conversion belongs in stt.py, not mic.py: mic.py intentionally stays dtype-agnostic; the conversion is a Moonshine requirement, not a microphone requirement
- FakeTranscriber fires on_line_completed during stop() to mirror the real Moonshine streaming lifecycle, enabling realistic unit tests without model access

## Deviations from Plan

None - plan executed exactly as written. The moonshine_voice API (Transcriber, TranscriptEventListener, get_model_for_language, remove_listener) matched the research exactly.

## Issues Encountered

None. moonshine-voice 0.0.49 installed cleanly on Windows. Model download completed in ~5 seconds. Import smoke test passed on first attempt.

## User Setup Required

None - Moonshine model was downloaded automatically during plan execution via `python -m moonshine_voice.download --language en`. Model is cached at `%LOCALAPPDATA%\moonshine_voice\`. No manual steps required.

## Next Phase Readiness

- transcribe() is ready to receive int16 arrays from mic.record_until_silence() — the int16 interface contract is fulfilled
- Phase 3 (TTS) can proceed independently; Phase 4 pipeline assembly will wire mic -> stt -> llm -> tts
- Concern from STATE.md still applies: ARM64 wheel availability for moonshine-voice on Pi OS Bookworm must be confirmed on physical hardware before deployment

---
*Phase: 02-stt-integration*
*Completed: 2026-03-10*
