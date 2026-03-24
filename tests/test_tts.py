"""Offline-safe unit tests for learnbox/tts.py."""

import numpy as np
import pytest
from unittest.mock import MagicMock


# --- strip_markdown tests (no mocking needed) ---

def test_strip_markdown_removes_bold():
    from learnbox.tts import strip_markdown
    assert strip_markdown("**photosynthesis**") == "photosynthesis"


def test_strip_markdown_removes_headings():
    from learnbox.tts import strip_markdown
    assert strip_markdown("## Summary") == "Summary"


def test_strip_markdown_removes_list_markers():
    from learnbox.tts import strip_markdown
    result = strip_markdown("- item one\n- item two")
    assert "- " not in result


def test_strip_markdown_passes_plain_text_unchanged():
    from learnbox.tts import strip_markdown
    text = "Photosynthesis is how plants make food."
    assert strip_markdown(text) == text


# --- speak() tests — patch _voice and play_audio to avoid model/hardware dependency ---

class FakePiperVoice:
    """Mock PiperVoice that returns predictable AudioChunk objects."""
    def synthesize(self, text):
        chunk = MagicMock()
        chunk.audio_int16_bytes = np.zeros(100, dtype=np.int16).tobytes()
        chunk.sample_rate = 22050
        yield chunk


def test_speak_calls_play_audio_with_int16(monkeypatch):
    import learnbox.tts as tts_module
    monkeypatch.setattr(tts_module, "_voice", FakePiperVoice())
    played = []
    # Patch the name as bound in tts.py (via `from learnbox.audio import play_audio`)
    monkeypatch.setattr(tts_module, "play_audio", lambda audio, sr: played.append((audio, sr)))
    tts_module.speak("Hello world")
    assert len(played) == 1
    assert played[0][0].dtype == np.int16
    assert played[0][1] == 22050


def test_speak_skips_empty_text(monkeypatch):
    import learnbox.tts as tts_module
    monkeypatch.setattr(tts_module, "_voice", FakePiperVoice())
    played = []
    # Patch the name as bound in tts.py (via `from learnbox.audio import play_audio`)
    monkeypatch.setattr(tts_module, "play_audio", lambda audio, sr: played.append((audio, sr)))
    tts_module.speak("")
    assert len(played) == 0
