from learnbox.mic import record_until_silence
from learnbox import stt  # noqa: F401 — triggers Moonshine model load at startup
from learnbox.stt import transcribe
from learnbox.llm import ask


def main():
    print("LearnBox — press Enter to speak, Ctrl+C to quit.\n")
    while True:
        try:
            input("[ Press Enter to speak ]")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        print("Listening...", flush=True)
        audio = record_until_silence()

        if len(audio) == 0:
            print("(no speech detected — try again)\n")
            continue

        transcript = transcribe(audio)

        if not transcript.strip():
            print("(could not transcribe — speak closer to the mic)\n")
            continue

        print(f"You: {transcript}")
        print("Thinking...", flush=True)

        try:
            response = ask(transcript, timeout=120.0)
            print(f"LearnBox: {response}\n")
        except RuntimeError as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
