"""
Speaker playback via sounddevice. Platform-neutral — same code runs on Windows and Pi 5.
Never hardcode device index.
"""

from math import gcd

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly


def _get_output_rate() -> int:
    """Return the default output device's native sample rate."""
    try:
        info = sd.query_devices(kind="output")
        return int(info["default_samplerate"])
    except Exception:
        return 44100


def _resample(audio: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
    if from_rate == to_rate:
        return audio
    g = gcd(from_rate, to_rate)
    up, down = to_rate // g, from_rate // g
    resampled = resample_poly(audio.astype(np.float32), up, down)
    return np.clip(resampled, -32768, 32767).astype(np.int16)


def play_audio(audio: np.ndarray, sample_rate: int) -> None:
    """
    Play audio through the default output device.

    Blocks until playback is complete. Resamples to the device's native
    rate if needed (e.g. Pi USB speaker requires 44100 Hz).

    Args:
        audio: 1-D numpy array of audio samples (int16 or float32).
        sample_rate: Sample rate of the audio content in Hz.
    """
    output_rate = _get_output_rate()
    resampled = _resample(audio, sample_rate, output_rate)
    sd.play(resampled, samplerate=output_rate)
    sd.wait()
