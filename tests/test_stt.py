"""
Offline-safe unit tests for learnbox/stt.py.

No real Moonshine model download or microphone hardware is required.
The module-level _transcriber is monkeypatched with FakeTranscriber where
the real Transcriber would otherwise be called.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

import learnbox.stt as stt_module
from learnbox.stt import transcribe


# ---------------------------------------------------------------------------
# FakeTranscriber — replaces module-level _transcriber in tests
# ---------------------------------------------------------------------------

class FakeTranscriber:
    """Drop-in replacement for moonshine_voice.Transcriber in unit tests."""

    def __init__(self, transcript_lines):
        self._listeners = []
        self._lines = transcript_lines

    def add_listener(self, listener):
        self._listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

    def start(self):
        pass

    def add_audio(self, audio, sample_rate):
        pass

    def stop(self):
        for line_text in self._lines:
            event = MagicMock()
            event.line.text = line_text
            for listener in self._listeners:
                listener.on_line_completed(event)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_transcribe_returns_empty_for_empty_audio():
    """
    Empty int16 array must return "" immediately — no model access needed.
    This exercises the early-return guard at the top of transcribe().
    """
    result = transcribe(np.zeros(0, dtype=np.int16))
    assert result == ""


def test_int16_to_float32_conversion_range():
    """
    The int16->float32 conversion (/ 32768.0) must keep values in [-1.0, 1.0]
    for the full int16 range. This is a pure numpy test — no model required.
    """
    # Full int16 range: -32768 to 32767
    extremes = np.array([-32768, -1, 0, 1, 32767], dtype=np.int16)
    converted = extremes.astype(np.float32) / 32768.0

    assert converted.dtype == np.float32
    assert float(converted.min()) >= -1.0
    assert float(converted.max()) <= 1.0
    # Exact boundary check: -32768 / 32768 == -1.0
    assert converted[0] == pytest.approx(-1.0)


def test_transcribe_joins_multiple_lines(monkeypatch):
    """
    When Moonshine fires on_line_completed twice, transcribe() must join
    both lines with a single space.
    """
    monkeypatch.setattr(stt_module, "_transcriber", FakeTranscriber(["Hello", "world"]))
    audio = np.ones(3200, dtype=np.int16)
    result = stt_module.transcribe(audio)
    assert result == "Hello world"


def test_transcribe_returns_empty_when_moonshine_finds_no_speech(monkeypatch):
    """
    When Moonshine fires no on_line_completed events (no speech detected),
    transcribe() must return "".
    """
    monkeypatch.setattr(stt_module, "_transcriber", FakeTranscriber([]))
    audio = np.ones(3200, dtype=np.int16)
    result = stt_module.transcribe(audio)
    assert result == ""


def test_transcribe_strips_whitespace(monkeypatch):
    """
    Leading/trailing whitespace in Moonshine output must be stripped.
    """
    monkeypatch.setattr(stt_module, "_transcriber", FakeTranscriber([" hello world  "]))
    audio = np.ones(3200, dtype=np.int16)
    result = stt_module.transcribe(audio)
    assert result == "hello world"
