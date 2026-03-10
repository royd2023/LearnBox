"""
Speaker playback via sounddevice. Platform-neutral — same code runs on Windows and Pi 5.
Never hardcode device index.
"""

import numpy as np
import sounddevice as sd


def play_audio(audio: np.ndarray, sample_rate: int) -> None:
    """
    Play audio through the default output device.

    Blocks until playback is complete. audio can be int16 or float32.
    sample_rate must match the audio content (e.g., 16000 for captured
    mic audio, 22050 for Piper TTS output in Phase 3).

    Args:
        audio: 1-D numpy array of audio samples. Both int16 and float32
            are accepted — sounddevice handles the format natively.
            Do not force a conversion before calling this function.
        sample_rate: Sample rate in Hz that matches the audio content.
    """
    sd.play(audio, samplerate=sample_rate)
    sd.wait()
