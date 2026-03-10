# Roadmap: LearnBox

## Overview

LearnBox starts with a working text-in, text-out LLM layer and extends it into a fully offline, voice-first pipeline. Phase 1 establishes the audio hardware foundation and cross-platform abstractions. Phase 2 adds the input half of the voice pipeline (mic capture and STT). Phase 3 adds the output half (TTS, playback, pipeline wiring, and display). Phase 4 validates the complete system on Pi 5 hardware and hardens it for real use. When all four phases are done, a student speaks a question and hears a clear spoken answer — entirely offline.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Audio Foundation** - Cross-platform audio capture, playback, and platform-neutral abstraction (completed 2026-03-10)
- [x] **Phase 2: STT Integration** - Moonshine speech-to-text wired to mic capture with push-to-talk gating (completed 2026-03-10)
- [ ] **Phase 3: TTS, Pipeline, and Display** - Piper TTS, full voice pipeline wiring, and on-screen text display
- [ ] **Phase 4: Pi Validation and Deployment** - Hardware validation, RAM/latency profiling, and deployment setup on Raspberry Pi 5

## Phase Details

### Phase 1: Audio Foundation
**Goal**: Audio capture and playback work reliably on both Windows and Pi 5 behind a platform-neutral interface
**Depends on**: Nothing (first phase)
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04
**Success Criteria** (what must be TRUE):
  1. Running the audio module on Windows captures microphone audio at 16kHz mono without error
  2. Energy-based VAD correctly detects speech start and end — silence does not trigger recording
  3. The system plays back a test audio clip through the default speaker
  4. The same audio code runs unchanged on both Windows and Linux (Pi 5) — no platform-specific branches in calling code
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Add sounddevice/numpy deps + implement mic capture with energy-based VAD
- [x] 01-02-PLAN.md — Implement audio playback + automated tests + human round-trip verification

### Phase 2: STT Integration
**Goal**: A spoken question is reliably transcribed to text using Moonshine on-device with visible listening feedback
**Depends on**: Phase 1
**Requirements**: STT-01, STT-02, STT-03, STT-04
**Success Criteria** (what must be TRUE):
  1. Pressing the push-to-talk key starts recording; releasing it stops recording and triggers transcription
  2. A clearly visible "Listening..." state is shown on screen while the mic is active
  3. A clearly visible "Thinking..." state is shown on screen while the LLM is generating
  4. A spoken school question ("What is photosynthesis?") transcribes to accurate text using Moonshine on-device
  5. An empty or inaudible recording does not pass an empty transcript downstream — the error is caught before reaching the LLM
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Add moonshine-voice dep + implement learnbox/stt.py + offline-safe tests
- [ ] 02-02-PLAN.md — Update main.py with PTT voice loop + human end-to-end verification

### Phase 3: TTS, Pipeline, and Display
**Goal**: The complete voice pipeline works end-to-end and the question and answer are shown on screen alongside audio
**Depends on**: Phase 2
**Requirements**: TTS-01, TTS-02, TTS-03, TTS-04, PIPE-01, PIPE-02, PIPE-03, PIPE-04, DISP-01, DISP-02
**Success Criteria** (what must be TRUE):
  1. A student asks a question aloud and hears a spoken answer — the full mic-to-speaker loop completes without manual intervention
  2. A short audio cue plays within 500ms of transcription completing, before the LLM response arrives — the device never appears frozen
  3. The transcribed question and LLM response are both shown as text on screen during and after the voice interaction
  4. The microphone does not capture audio while TTS is playing — the system cannot trigger itself
  5. An error at any pipeline stage (empty transcript, LLM timeout, TTS failure) produces a spoken error message rather than silent failure
**Plans**: TBD

### Phase 4: Pi Validation and Deployment
**Goal**: The complete system runs reliably on Raspberry Pi 5 within the hardware constraints and can be set up from scratch offline
**Depends on**: Phase 3
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):
  1. Running the setup script on a fresh Pi OS Bookworm install installs all dependencies (Moonshine, Piper, sounddevice) without internet access after initial model pre-staging
  2. All model assets (Ollama qwen2.5:1.5b, Moonshine base-en, Piper en_US-lessac-medium) are present and functional after running the setup script
  3. Peak RAM usage with all models loaded stays at or below 2GB — confirmed with `free -m` on the physical Pi
  4. End-to-end latency from question spoken to spoken answer begins within 10 seconds on Pi 5 hardware
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Audio Foundation | 2/2 | Complete    | 2026-03-10 |
| 2. STT Integration | 1/2 | Complete    | 2026-03-10 |
| 3. TTS, Pipeline, and Display | 0/TBD | Not started | - |
| 4. Pi Validation and Deployment | 0/TBD | Not started | - |
