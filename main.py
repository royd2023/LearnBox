from learnbox.mic import record_until_silence
from learnbox import stt    # noqa: F401 — triggers Moonshine model load at startup
from learnbox.stt import transcribe
from learnbox.llm import ask
from learnbox import tts    # noqa: F401 — triggers Piper voice model load at startup
from learnbox.tts import speak, speak_error, play_thinking_cue


def main():
    print("LearnBox — press Enter to speak, Ctrl+C to quit.\n")
    while True:
        try:
            input("[ Press Enter to speak ]")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        # --- MIC ---
        print("Listening...", flush=True)
        try:
            audio = record_until_silence()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

        if len(audio) == 0:
            print("(no speech detected — try again)\n")
            continue

        # --- STT ---
        transcript = transcribe(audio)
        if not transcript.strip():
            print("(could not transcribe — speak closer to the mic)\n")
            continue

        print(f"You: {transcript}", flush=True)   # DISP-01

        # --- THINKING CUE ---
        play_thinking_cue()   # TTS-02: plays before LLM call; <500ms

        # --- LLM ---
        print("Thinking...", flush=True)
        try:
            response = ask(transcript, timeout=120.0)
        except RuntimeError as e:
            speak_error(f"Sorry, I could not get an answer. {e}")
            continue

        print(f"LearnBox: {response}\n", flush=True)  # DISP-02

        # --- TTS ---
        print("Speaking...", flush=True)   # TTS-04
        try:
            speak(response)
        except Exception as e:
            print(f"(TTS failed: {e})\n", flush=True)


if __name__ == "__main__":
    main()
