# Feature Landscape

**Domain:** Offline voice-first educational assistant (ages 8-18, Raspberry Pi 5)
**Researched:** 2026-03-10
**Overall confidence:** MEDIUM — research tools unavailable; findings based on training data (knowledge of Moonshine, Piper, Ollama, voice-UX patterns for education). Confidence notes per section.

---

## Table Stakes

Features users expect from any voice-first educational assistant. Missing = product feels broken or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Wake-word or push-to-talk trigger | Students need a defined moment to speak; without it, the mic never knows when to listen | Low | Push-to-talk (button press) is simpler and more reliable on Pi than always-on wake-word. Wake-word requires a secondary always-on model. Recommend push-to-talk for v1. |
| Visual + audio feedback during listening | Without "I'm listening" signal, students repeat themselves or speak at wrong times | Low | A simple "Listening..." indicator on screen + optional beep tone. |
| Audible spoken answer (TTS output) | Core product promise — hearing the answer is the value proposition | Low | Piper handles this. Voice must sound natural enough for ages 8-18 to find tolerable. |
| Text display of question and answer | Students need to see what was transcribed — confirms the system heard them correctly; also supports re-reading | Low | Already in PROJECT.md requirements. Screen is assumed present. |
| Processing indicator ("Thinking...") | Without a loading state, students assume the device is broken and interrupt the process | Low | Already present in current CLI `main.py`. Must carry forward to voice UI. |
| Graceful error recovery with spoken feedback | Mic failed, LLM timed out, transcription returned empty — student must hear what went wrong | Low-Med | "Sorry, I didn't catch that" is the minimum. Must avoid silent failure. |
| Age-appropriate language in all spoken output | System responses must be understood by an 8-year-old, not just an 18-year-old | Low | System prompt already tuned for this in `llm.py`. Must persist through TTS pipeline without modification. |
| Response in under 10 seconds | Kids (especially younger ones) have low tolerance for latency; >10s = "it's broken" | Med | Per PROJECT.md constraint. Moonshine + qwen2.5:1.5b + Piper chain must fit this budget on Pi 5. Needs profiling. |
| Silent background operation | Device must not randomly blurt out sound or react to ambient noise | Low | Gated by push-to-talk or very tight VAD. Always-listening risks ambient triggers. |
| Stable boot-to-ready state | In a school/home setting, device must reliably reach ready state without manual intervention | Med | Requires systemd/autostart setup. Not a v1 feature but needed before any real deployment. |

**Confidence:** MEDIUM. The expectations listed are grounded in established voice UX principles and child-computer interaction research patterns. The specific latency tolerance of 10s for ages 8-18 aligns with PROJECT.md's own stated constraint.

---

## Differentiators

Features that make LearnBox stand out from alternatives (Alexa, Google, web search). Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Fully offline operation | Works without internet — usable in low-income areas, rural schools, places without reliable Wi-Fi | High (already achieved for LLM; completing with STT+TTS) | This is the primary differentiator. Most competitors require cloud. Once the pipeline is complete, this is a hard advantage. |
| No account / no login / instant use | Zero barrier to entry — a child can pick it up and ask a question immediately | Low | Explicitly out of scope per PROJECT.md. A strong differentiator over anything requiring login. Keep it. |
| Honest uncertainty — refuses to confabulate | LLM prompt enforces "only state facts you are confident are correct" — prevents dangerous misinformation for students | Low (prompt-level) | Rare in educational AI. Most assistants guess confidently. This differentiates on trust. |
| Age-adaptive explanation style | System prompt currently targets ages 8-18 broadly. Could adapt to detected grade level via simple selector | Med | Even a 3-way selector (junior/middle/senior) in v1 would be notable. Defer until base pipeline is stable. |
| Persistent question history (session) | Seeing a list of previous questions in the same session helps students review what they asked | Low | In-memory only (no database). Useful for screen display. Single session, not cross-session. Low risk. |
| Audio replay of last answer | Student missed what was said; press a button to hear it again | Low | Requires buffering the last Piper output. Simple and very user-valued for students. |
| Teacher/parent "topic lock" (subject filtering) | Allow a teacher to restrict questions to a subject area — e.g., only maths | Med | Requires a configuration mode. Useful for classroom deployment. Defer to post-v1. |
| Multilingual voice support | Piper supports many languages; students in multilingual households benefit | High | Piper has extensive language support. Moonshine is English-only at time of training data (verify before claiming). Blocks multilingual STT without a different STT model. Note as future direction only. |

**Confidence:** MEDIUM. Offline operation and no-login differentiation are verified by project constraints. The Moonshine English-only limitation is from training data — LOW confidence, verify against current Moonshine docs before implementing multilingual features.

---

## Anti-Features

Features to explicitly NOT build in v1. Building these would add scope, complexity, or risk without proportional benefit at this stage.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Always-on wake-word detection | Requires a secondary always-on model (Porcupine, Snowboy, OpenWakeWord) adding ~50-100MB RAM and continuous CPU use on Pi 5. Complex VAD tuning. High false-trigger rate in noisy classrooms. | Use push-to-talk: a physical button or keyboard key. Reliable, zero extra RAM, no false triggers. |
| User profiles / session persistence across reboots | Requires a database, user management, privacy considerations. Age 8-18 users in a school setting create COPPA/GDPR-like concerns even offline. | Stateless per-session. Each session starts fresh. Simple and safe. |
| Streaming TTS (word-by-word audio) | Piper works best generating complete utterances. Attempting to stream partial LLM output into Piper mid-sentence requires complex buffer management, creates awkward pauses, and the LLM response is only 2-3 sentences anyway. | Buffer full LLM response, then synthesize and play the whole thing. 2-3 sentences synthesizes in well under 2 seconds on Pi 5. |
| Web/API exposure | Even a local web UI adds Flask/FastAPI, networking, security surface. The product is a physical device with a screen — not a browser app. | CLI or lightweight GUI (tkinter/pygame). No networking layer needed. |
| Curriculum alignment / lesson plans | Requires structured content, curriculum databases, alignment to national standards — a separate product. | General Q&A. Students ask what they need. No curriculum curation needed. (Explicitly out of scope per PROJECT.md.) |
| Spelling/pronunciation correction of student speech | Moonshine transcribes what it hears; "correcting" the student's question back to them is paternalistic and confusing for younger kids. | Pass transcription directly to LLM. Let LLM handle ambiguous phrasing naturally. |
| Background music / ambient sound | Adds audio mixing complexity, competes with TTS output, zero educational value. | Silence except for TTS responses. |
| Confidence scoring displayed to user | Moonshine may expose a confidence value; showing it to an 8-year-old ("I'm 73% sure") is confusing and erodes trust. | Use confidence internally only (e.g., to decide whether to ask "Did you say X?"). |
| Internet fallback | Explicitly out of scope. Even as a "nice to have" it undermines the offline-first value proposition and adds network-dependency complexity. | Stay fully offline. This is a feature, not a limitation. |
| Gamification (points, streaks, badges) | Requires persistent storage, user identity, reward loop design — a different product. Not needed for v1 utility. | The answer IS the reward. Keep it simple. |

**Confidence:** HIGH for anti-features. These are grounded in hardware constraints (2GB RAM), project scope constraints (PROJECT.md), and established voice UX anti-patterns.

---

## Feature Dependencies

Dependencies between features — what must exist before what can be built.

```
Microphone capture (raw audio)
  → Moonshine STT (transcription to text)
    → Ollama LLM (text response)
      → Piper TTS (text to audio)
        → Speaker playback (audio output)

This is the core pipeline. Everything else depends on it being stable.

Push-to-talk trigger
  → Microphone capture (gated by trigger)

Visual display (screen)
  → Text display of question
  → Text display of answer
  → Processing indicator ("Thinking...")
  → Persistent question history (session)

Moonshine STT
  → Transcription confidence (internal use only)
    → "Did you say X?" clarification prompt (optional, post-v1)

Piper TTS
  → Audio playback buffer
    → Audio replay of last answer

Full voice pipeline (stable)
  → Age-adaptive explanation style (system prompt variant)
  → Teacher/parent topic lock (configuration layer)
  → Autostart / boot-to-ready (deployment hardening)
```

**Critical path:** Microphone capture → Moonshine → Ollama → Piper → Speaker. Everything else is layered on top.

---

## MVP Recommendation

The Milestone scope is: "Adding Moonshine STT and Piper TTS to complete the voice pipeline." The LLM layer is done. MVP for this milestone is the minimal voice pipeline that a student can actually use.

**Must have (this milestone):**

1. Push-to-talk trigger (button/key press starts and stops recording)
2. Microphone audio capture (correct sample rate, format for Moonshine)
3. Moonshine STT transcription (text from audio)
4. Ollama LLM response (already done — wire it in)
5. Piper TTS synthesis (text to audio file/stream)
6. Speaker playback (play the Piper output)
7. Screen text display (question + answer + thinking indicator)
8. Spoken + visual error handling ("I didn't catch that" for empty transcriptions)
9. End-to-end latency within ~10s on Pi 5

**Include in this milestone (low complexity, high value):**

10. Audio replay of last answer (buffer Piper output, replay button)
11. Session question history displayed on screen (in-memory list)

**Defer to post-milestone:**

- Wake-word detection — complexity/RAM cost not worth it until push-to-talk is validated
- Age-adaptive explanation style — system prompt experiment, not pipeline work
- Teacher topic lock — requires configuration UI layer
- Autostart / boot-to-ready — deployment hardening, separate milestone
- Multilingual support — blocked by Moonshine English constraint (verify first)

---

## User Expectation Analysis

### Student Perspective (ages 8-18)

**What breaks trust immediately:**
- Silent failure (device does nothing, no feedback)
- Wrong transcription with no way to see what was heard
- Response time >15 seconds (feels frozen)
- Adult vocabulary in answers (loses younger students)
- TTS voice that sounds robotic/creepy (uncanny valley effect)

**What builds trust quickly:**
- "I'm listening" feedback the instant they trigger the device
- Seeing their words on screen (confirms the machine understood)
- Fast, clear spoken answer
- The answer being correct and age-appropriate

**Younger students (8-12):** Need shorter answers, simpler words, quicker feedback. The 2-3 sentence prompt constraint is well-calibrated here.

**Older students (13-18):** Tolerate slightly longer latency but are less forgiving of wrong answers. May ask follow-up questions in rapid succession.

### Teacher/Parent Perspective

**Primary concern:** Does it give correct answers? (The qwen2.5:1.5b benchmark validation directly addresses this.)

**Secondary concerns:**
- Does it say anything inappropriate? (System prompt safety language mitigates this but cannot fully prevent it — important to acknowledge)
- Can I control what subjects it's used for? (Topic lock — post-v1)
- Does it store what my child asked? (No — stateless, no persistence, a genuine advantage)

**Confidence:** MEDIUM. Based on established patterns in child-computer interaction literature and classroom technology adoption research. Not verified against specific user studies.

---

## Sources

- Project context: `C:/Users/rdinh/Documents/CODE/LearnBox/LearnBox/.planning/PROJECT.md` (HIGH confidence — primary source)
- Existing LLM implementation: `C:/Users/rdinh/Documents/CODE/LearnBox/LearnBox/learnbox/llm.py` (HIGH confidence — directly informs feature constraints)
- Moonshine STT capabilities: Training data knowledge, August 2025 cutoff (MEDIUM confidence — verify current language support and API surface before implementing multilingual features)
- Piper TTS capabilities: Training data knowledge, August 2025 cutoff (MEDIUM confidence — voice catalog and Pi 5 performance characteristics should be verified against current Piper releases)
- Voice UX patterns for children: Training data synthesis from child-computer interaction research (MEDIUM confidence — general principles well-established, specific thresholds like 10s latency are project-defined)
- WebSearch/WebFetch: Unavailable during this research session (all findings flagged with training-data confidence levels where relevant)
