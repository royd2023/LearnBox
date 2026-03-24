"""
Text-to-speech synthesis using Piper (en_US-lessac-medium).

Input: plain text string (LLM response, stripped of markdown)
Output: blocking audio playback via audio.play_audio()

The PiperVoice is loaded once at module import and reused for the
lifetime of the process. Model files must exist at:
    <project_root>/models/en_US-lessac-medium.onnx
    <project_root>/models/en_US-lessac-medium.onnx.json

If model files are absent, import raises RuntimeError with setup instructions.
Run once to download:
    python3 -m piper.download_voices en_US-lessac-medium --data-dir models/
"""

import re
from pathlib import Path
from typing import Optional

import numpy as np

from learnbox.audio import play_audio

MODEL_PATH = Path(__file__).parent.parent / "models" / "en_US-lessac-medium.onnx"

if not MODEL_PATH.exists():
    raise RuntimeError(
        f"Piper voice model not found at {MODEL_PATH}.\n"
        "Run: python3 -m piper.download_voices en_US-lessac-medium --data-dir models/"
    )

from piper.voice import PiperVoice  # noqa: E402 — import after path check

# Load once — PiperVoice initialization is slow (~200-500ms ONNX session init)
_voice = PiperVoice.load(str(MODEL_PATH))

# Thinking cue constants
_CUE_SAMPLE_RATE = 22050
_CUE_DURATION_S = 0.3      # 300ms — within TTS-02 500ms budget
_CUE_FREQUENCY = 440       # A4


def play_thinking_cue() -> None:
    """Play a short 440 Hz tone to signal processing has started (TTS-02)."""
    t = np.linspace(0, _CUE_DURATION_S, int(_CUE_SAMPLE_RATE * _CUE_DURATION_S), endpoint=False)
    tone = (np.sin(2 * np.pi * _CUE_FREQUENCY * t) * 16383).astype(np.int16)
    play_audio(tone, _CUE_SAMPLE_RATE)


def strip_markdown(text: str) -> str:
    """Remove markdown formatting from LLM response text before synthesis (TTS-03)."""
    text = re.sub(r'\*{1,2}([^*\n]+)\*{1,2}', r'\1', text)      # **bold**, *italic*
    text = re.sub(r'_{1,2}([^_\n]+)_{1,2}', r'\1', text)         # __bold__, _italic_
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)    # ## Headings
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)   # - list items
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # 1. ordered list
    text = re.sub(r'```[\s\S]*?```', '', text)                     # code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)                       # inline code
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def speak(text: str) -> None:
    """Synthesize text to speech and play it blocking (TTS-01).

    Strips markdown before synthesis. Returns immediately if text is empty.
    """
    clean = strip_markdown(text)
    if not clean.strip():
        return

    all_audio = []
    sample_rate: Optional[int] = None
    for chunk in _voice.synthesize(clean):
        int_data = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
        all_audio.append(int_data)
        if sample_rate is None:
            sample_rate = chunk.sample_rate  # 22050 Hz for lessac-medium

    if all_audio and sample_rate:
        play_audio(np.concatenate(all_audio), sample_rate)


def speak_error(message: str) -> None:
    """Speak an error message; falls back to print if TTS itself fails (PIPE-04)."""
    try:
        speak(message)
    except Exception:
        print(f"[TTS failed — error]: {message}", flush=True)
