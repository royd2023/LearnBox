"""
Speech-to-text transcription using Moonshine base-en.

Input: int16 numpy array at 16kHz (from mic.py record_until_silence())
Output: transcribed string, or empty string if no speech detected.

The Transcriber is loaded once at module import and reused for the
lifetime of the process. Model loads from ~/.cache/moonshine_voice/
(Linux) or %LOCALAPPDATA%\\moonshine_voice\\ (Windows).

If the model cache is absent, import raises an error. Run:
    python -m moonshine_voice.download --language en
"""

import numpy as np
from moonshine_voice import Transcriber, TranscriptEventListener, get_model_for_language

# Load once — Transcriber initialization is slow (~200-500ms on Pi 5)
_model_path, _model_arch = get_model_for_language("en")
_transcriber = Transcriber(model_path=_model_path, model_arch=_model_arch)

SAMPLE_RATE = 16000  # must match mic.py SAMPLE_RATE
CHUNK_SIZE = 1600    # 100ms at 16kHz — matches mic.py CHUNK_FRAMES


class _LineCollector(TranscriptEventListener):
    def __init__(self):
        self.lines: list[str] = []

    def on_line_completed(self, event):
        self.lines.append(event.line.text)


def transcribe(audio_int16: np.ndarray) -> str:
    """
    Transcribe a pre-recorded int16 audio array using Moonshine base-en.

    Args:
        audio_int16: 1-D numpy array, dtype=int16, at SAMPLE_RATE Hz.
                     From mic.record_until_silence(). May be empty (len 0).

    Returns:
        Transcribed text string. Returns "" if audio is empty or Moonshine
        finds no speech. Caller must guard against empty return value.
    """
    if len(audio_int16) == 0:
        return ""

    # Moonshine requires float32 in [-1.0, 1.0]
    # Division by 32768.0 (not 32767.0) — standard PCM normalization
    audio_float32 = audio_int16.astype(np.float32) / 32768.0

    listener = _LineCollector()
    _transcriber.add_listener(listener)
    try:
        _transcriber.start()
        for i in range(0, len(audio_float32), CHUNK_SIZE):
            _transcriber.add_audio(audio_float32[i : i + CHUNK_SIZE], SAMPLE_RATE)
        _transcriber.stop()
    finally:
        _transcriber.remove_listener(listener)

    return " ".join(listener.lines).strip()
