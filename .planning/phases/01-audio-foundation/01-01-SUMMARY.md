---
plan: 01-01
phase: 01-audio-foundation
status: complete
---

# Summary: 01-01 — Dependencies + mic.py

## What Was Built

- `requirements.txt` updated with `sounddevice>=0.5.5` and `numpy>=1.24.0`
- `learnbox/mic.py` implemented with energy-based VAD

## Key Files

### created
- `learnbox/mic.py`

### modified
- `requirements.txt`

## Decisions Made

- Captures at 16kHz mono int16 — Moonshine requires float32, conversion responsibility documented in docstring for Phase 2 implementer
- Energy VAD uses RMS threshold of 300 (int16 scale), configurable via `calibrate_silence()`
- 15-second safety cap (MAX_RECORD_CHUNKS=150) prevents unbounded capture
- No `device=` ever passed to sounddevice — system default always used (platform neutral)

## Self-Check: PASSED

All verification checks passed:
- `pip install -r requirements.txt` exits 0
- sounddevice 0.5.5, numpy 2.4.2 import cleanly
- `SAMPLE_RATE == 16000` ✓
- `record_until_silence(threshold=10000)` returns `dtype=int16, zeros=True` with no speech ✓
- `device=` only appears in a docstring comment, not in any sounddevice call ✓
