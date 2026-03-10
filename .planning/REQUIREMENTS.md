# Requirements: LearnBox

**Defined:** 2026-03-10
**Core Value:** A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.

## v1 Requirements

### Audio

- [ ] **AUD-01**: System captures microphone audio at 16kHz mono on both Windows and Pi 5
- [ ] **AUD-02**: System uses energy-based VAD to detect start and end of speech
- [ ] **AUD-03**: System plays synthesized audio through the default speaker
- [ ] **AUD-04**: Audio capture and playback are abstracted behind a platform-neutral interface (Windows/Linux)

### STT

- [ ] **STT-01**: System transcribes spoken input to text using Moonshine (base-en) on-device
- [ ] **STT-02**: System uses push-to-talk gating (button/key press) to start listening
- [ ] **STT-03**: System shows a "listening" feedback state while recording
- [ ] **STT-04**: System shows a "thinking" feedback state while LLM is generating

### TTS

- [ ] **TTS-01**: System synthesizes LLM text responses to speech using Piper on-device
- [ ] **TTS-02**: System plays a short "thinking" audio cue immediately after transcription (before LLM response)
- [ ] **TTS-03**: System strips markdown formatting from LLM response before synthesis
- [ ] **TTS-04**: System shows a "speaking" feedback state during audio playback

### Pipeline

- [ ] **PIPE-01**: Full pipeline works end-to-end: Mic → Moonshine → Ollama → Piper → Speaker
- [ ] **PIPE-02**: All models (Moonshine, Ollama, Piper) are loaded once at startup, not per-turn
- [ ] **PIPE-03**: Mic does not capture while TTS is playing (no self-triggering)
- [ ] **PIPE-04**: Pipeline handles errors at each stage with a spoken error message

### Display

- [ ] **DISP-01**: Screen displays the transcribed student question as text
- [ ] **DISP-02**: Screen displays the LLM response as text alongside audio playback

### Deployment

- [ ] **DEPLOY-01**: Setup script installs all dependencies (Moonshine, Piper, sounddevice) on Pi 5
- [ ] **DEPLOY-02**: Setup script pre-stages Ollama model and Piper voice model for offline use
- [ ] **DEPLOY-03**: System runs within 2GB RAM on Raspberry Pi 5
- [ ] **DEPLOY-04**: End-to-end latency (question → spoken answer) is under 10 seconds on Pi 5

## v2 Requirements

### Wake Word

- **WAKE-01**: System listens for a wake word to start recording (instead of push-to-talk)

### Audio Replay

- **REPLAY-01**: Student can replay the last response
- **REPLAY-02**: Student can view session history of Q&A pairs

### Multilingual

- **LANG-01**: System supports non-English student questions (pending Moonshine language support)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud/internet LLM fallback | Hard constraint — fully offline |
| User accounts or profiles | No login, anyone can use it |
| Curriculum alignment | General Q&A only for v1 |
| Streaming TTS (token-by-token) | Produces choppy audio — full response synthesis only |
| Always-on wake word detection | Too much RAM overhead on Pi 5 for v1 |
| Web UI | Pi hardware form factor, not a browser app |
| Gamification | Out of v1 scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUD-01 | Phase 1 | Pending |
| AUD-02 | Phase 1 | Pending |
| AUD-03 | Phase 1 | Pending |
| AUD-04 | Phase 1 | Pending |
| STT-01 | Phase 2 | Pending |
| STT-02 | Phase 2 | Pending |
| STT-03 | Phase 2 | Pending |
| STT-04 | Phase 2 | Pending |
| TTS-01 | Phase 3 | Pending |
| TTS-02 | Phase 3 | Pending |
| TTS-03 | Phase 3 | Pending |
| TTS-04 | Phase 3 | Pending |
| PIPE-01 | Phase 3 | Pending |
| PIPE-02 | Phase 3 | Pending |
| PIPE-03 | Phase 3 | Pending |
| PIPE-04 | Phase 3 | Pending |
| DISP-01 | Phase 3 | Pending |
| DISP-02 | Phase 3 | Pending |
| DEPLOY-01 | Phase 4 | Pending |
| DEPLOY-02 | Phase 4 | Pending |
| DEPLOY-03 | Phase 4 | Pending |
| DEPLOY-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-10*
*Last updated: 2026-03-10 after initial definition*
