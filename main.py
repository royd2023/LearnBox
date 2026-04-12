try:
    from gpiozero import Button as _GPIOButton
    _button = _GPIOButton(17, pull_up=True)
    _USE_GPIO = True
except Exception:
    _button = None
    _USE_GPIO = False

from learnbox.mic import record_until_silence, calibrate_silence
from learnbox import stt    # noqa: F401 — triggers Moonshine model load at startup
from learnbox.stt import transcribe
from learnbox.llm import stream_ask
from learnbox import tts    # noqa: F401 — triggers Piper voice model load at startup
from learnbox.tts import speak_streaming, speak_error, play_thinking_cue


def _wait_for_trigger():
    """Block until button press (Pi) or Enter key (fallback)."""
    if _USE_GPIO:
        print("[ Press button to speak ]", flush=True)
        _button.wait_for_press()
    else:
        input("[ Press Enter to speak ]")


def main():
    if _USE_GPIO:
        print("LearnBox — press the button to speak, Ctrl+C to quit.\n")
    else:
        print("LearnBox — press Enter to speak, Ctrl+C to quit.\n")
    print("Calibrating microphone...", flush=True)
    silence_threshold = calibrate_silence()
    print(f"Mic calibrated (threshold: {silence_threshold})\n", flush=True)
    while True:
        try:
            _wait_for_trigger()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        # --- MIC ---
        print("Listening...", flush=True)
        try:
            audio = record_until_silence(silence_threshold=silence_threshold)
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

        # --- LLM + TTS (streaming) ---
        print("Thinking...", flush=True)
        try:
            response = speak_streaming(stream_ask(transcript, timeout=120.0))
        except RuntimeError as e:
            speak_error(f"Sorry, I could not get an answer. {e}")
            continue
        except Exception as e:
            print(f"(TTS failed: {e})\n", flush=True)
            continue

        print(f"LearnBox: {response}\n", flush=True)  # DISP-02


if __name__ == "__main__":
    main()
