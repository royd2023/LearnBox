# LearnBox

## What This Is

LearnBox is a fully offline, voice-first educational assistant for students aged 8-18. It runs on-device (Raspberry Pi 5 for production, Windows for development) and answers student questions across general knowledge, maths, science, and languages using a local LLM. Students speak a question, hear an answer — no internet, no account, no cloud.

## Core Value

A student can ask any school question out loud and get a clear, accurate spoken answer — entirely offline.

## Requirements

### Validated

- ✓ Local LLM (qwen2.5:1.5b via Ollama) answers student questions accurately — existing

### Active

- [ ] Moonshine transcribes spoken student input to text on-device
- [ ] Piper converts LLM text responses to spoken audio on-device
- [ ] Full voice pipeline: Mic → Moonshine → Ollama → Piper → Speaker
- [ ] Screen displays the question and answer text alongside audio
- [ ] System prompt tuned for ages 8-18, concise and accurate responses
- [ ] Pipeline runs on Raspberry Pi 5 within 2GB RAM

### Out of Scope

- Internet/cloud LLM fallback — fully offline is a hard constraint
- User accounts or profiles — no login, anyone can use it
- Subject-specific curriculum alignment — general Q&A only for v1
- Mobile app — Pi 5 hardware is the target form factor

## Context

- Development and testing on Windows; production target is Raspberry Pi 5
- LLM already working: qwen2.5:1.5b via Ollama, `learnbox/llm.py` wraps the API
- Model evaluated against 10 benchmark questions — 1.5b chosen over 0.5b for accuracy
- System prompt: friendly tutor, 2-3 sentences max, confident facts only
- STT: Moonshine (on-device, no cloud)
- TTS: Piper (on-device, no cloud)
- Pipeline must stay within ~2GB RAM on Pi 5

## Constraints

- **Hardware**: Raspberry Pi 5, 2GB RAM target — all components must fit
- **Connectivity**: Fully offline — no internet dependency at runtime
- **Stack**: Python, Ollama (qwen2.5:1.5b), Moonshine (STT), Piper (TTS)
- **Latency**: Acceptable latency for a student interaction (target <10s end-to-end on Pi 5)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| qwen2.5:1.5b over 0.5b | 0.5b had 2+ wrong answers in benchmark; 1.5b passed all 10 | — Pending validation |
| Ollama for LLM serving | Simple HTTP API, cross-platform, Pi 5 viable | — Pending |
| Moonshine for STT | On-device, no cloud, designed for edge hardware | — Pending |
| Piper for TTS | On-device, fast, lightweight, Raspberry Pi compatible | — Pending |

---
*Last updated: 2026-03-10 after initialization*
