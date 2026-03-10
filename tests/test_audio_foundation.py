"""
Automated unit tests for learnbox/mic.py and learnbox/audio.py.

Offline-safe: no real microphone or speaker is required. sounddevice is
patched wherever needed so these tests run in CI with no audio hardware.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, call

from learnbox.mic import record_until_silence, SAMPLE_RATE
from learnbox.audio import play_audio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeStream:
    """Context-manager mock for sd.InputStream that yields pre-defined chunks."""

    def __init__(self, chunks):
        self._chunks = iter(chunks)

    def read(self, frames):
        try:
            return next(self._chunks), False
        except StopIteration:
            return np.zeros((frames, 1), dtype=np.int16), False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# TestMicModule
# ---------------------------------------------------------------------------

class TestMicModule:

    def test_sample_rate_constant(self):
        assert SAMPLE_RATE == 16000

    def test_record_returns_int16(self, monkeypatch):
        """
        5 silent chunks (below threshold), then 5 loud chunks (speech onset),
        then 15 silent chunks (triggers stop after silence_duration_chunks=10).
        Result must be non-empty int16 with ndim==1.
        """
        silent_chunk = np.zeros((1600, 1), dtype=np.int16)
        loud_chunk = np.ones((1600, 1), dtype=np.int16) * 1000

        chunks = (
            [silent_chunk] * 5
            + [loud_chunk] * 5
            + [silent_chunk] * 15
        )

        monkeypatch.setattr(
            "learnbox.mic.sd.InputStream",
            lambda **kwargs: FakeStream(chunks),
        )

        result = record_until_silence(
            silence_threshold=300,
            silence_duration_chunks=10,
        )

        assert result.dtype == np.int16
        assert result.ndim == 1
        assert len(result) > 0

    def test_record_returns_empty_on_silence_only(self, monkeypatch):
        """
        60 chunks of zeros — no speech onset ever detected.
        record_until_silence must return an empty array.
        """
        silent_chunk = np.zeros((1600, 1), dtype=np.int16)
        chunks = [silent_chunk] * 60

        monkeypatch.setattr(
            "learnbox.mic.sd.InputStream",
            lambda **kwargs: FakeStream(chunks),
        )

        result = record_until_silence(silence_threshold=300)
        assert len(result) == 0

    def test_no_hardcoded_device_index(self):
        """mic.py must never pass device= as a keyword arg to sounddevice calls."""
        import ast

        src = open("learnbox/mic.py").read()
        tree = ast.parse(src)

        sd_call_device_args = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(getattr(node, "func", None), ast.Attribute)
            and getattr(node.func, "attr", None) in {"InputStream", "OutputStream", "play", "rec"}
            and any(kw.arg == "device" for kw in node.keywords)
        ]
        assert sd_call_device_args == [], (
            f"Found hardcoded device= in {len(sd_call_device_args)} sounddevice call(s) in mic.py"
        )


# ---------------------------------------------------------------------------
# TestAudioModule
# ---------------------------------------------------------------------------

class TestAudioModule:

    def test_play_audio_calls_sd_play_and_wait(self, monkeypatch):
        """
        play_audio must call sd.play exactly once and sd.wait exactly once,
        proving the blocking contract is upheld without touching real hardware.
        """
        play_mock = MagicMock()
        wait_mock = MagicMock()

        monkeypatch.setattr("learnbox.audio.sd.play", play_mock)
        monkeypatch.setattr("learnbox.audio.sd.wait", wait_mock)

        audio = np.zeros(100, dtype=np.int16)
        play_audio(audio, 16000)

        play_mock.assert_called_once()
        wait_mock.assert_called_once()

    def test_play_audio_no_hardcoded_device(self):
        """audio.py must never pass device= as a keyword arg to sounddevice calls."""
        import ast

        src = open("learnbox/audio.py").read()
        tree = ast.parse(src)

        sd_call_device_args = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(getattr(node, "func", None), ast.Attribute)
            and getattr(node.func, "attr", None) in {"InputStream", "OutputStream", "play", "rec"}
            and any(kw.arg == "device" for kw in node.keywords)
        ]
        assert sd_call_device_args == [], (
            f"Found hardcoded device= in {len(sd_call_device_args)} sounddevice call(s) in audio.py"
        )

    def test_play_audio_accepts_float32(self, monkeypatch):
        """play_audio must accept float32 arrays without raising exceptions."""
        monkeypatch.setattr("learnbox.audio.sd.play", MagicMock())
        monkeypatch.setattr("learnbox.audio.sd.wait", MagicMock())

        audio = np.zeros(100, dtype=np.float32)
        play_audio(audio, 22050)  # must not raise
