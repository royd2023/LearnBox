"""
Audio capture with energy-based VAD.

Returns int16 at 16kHz mono. Caller (stt.py) is responsible for
float32 conversion before Moonshine:
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
"""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000       # Hz — required for Moonshine compatibility (Phase 2)
CHANNELS = 1              # mono
DTYPE = "int16"           # Moonshine needs float32 but STT layer handles conversion
CHUNK_FRAMES = 1600       # 100ms per chunk at 16kHz
DEFAULT_SILENCE_RMS = 300 # int16-scale RMS; tune per environment
SILENCE_CHUNKS = 10       # 1.0s consecutive silence = end of speech
MAX_RECORD_CHUNKS = 150   # 15s max recording cap — prevents unbounded capture


def list_devices() -> None:
    """Print all available audio devices. Used for remote Pi debugging."""
    print(sd.query_devices())


def calibrate_silence(duration_s: float = 1.0) -> int:
    """
    Sample the ambient noise level from the default input device.

    Records ``duration_s`` seconds of silence, computes the RMS of all
    captured chunks, and returns ``max(100, int(2 * ambient_rms))``.
    The returned value is suitable as the ``silence_threshold`` argument
    to ``record_until_silence()``.

    Args:
        duration_s: How many seconds to sample. Default 1.0.

    Returns:
        An integer silence threshold >= 100.
    """
    num_chunks = max(1, int(duration_s * SAMPLE_RATE / CHUNK_FRAMES))
    all_frames: list[np.ndarray] = []

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
    ) as stream:
        for _ in range(num_chunks):
            chunk, _ = stream.read(CHUNK_FRAMES)
            all_frames.append(chunk)

    combined = np.concatenate(all_frames, axis=0)
    ambient_rms = float(np.sqrt(np.mean(combined.astype(np.float32) ** 2)))
    threshold = max(100, int(2 * ambient_rms))
    print(f"Ambient RMS: {ambient_rms:.1f}  |  Silence threshold set to: {threshold}")
    return threshold


def record_until_silence(
    silence_threshold: int = DEFAULT_SILENCE_RMS,
    silence_duration_chunks: int = SILENCE_CHUNKS,
) -> np.ndarray:
    """
    Capture microphone audio until a silence period ends the utterance.

    Uses the system default input device (no ``device=`` argument is
    ever passed to InputStream). Opens the stream at SAMPLE_RATE Hz,
    mono, int16. Reads CHUNK_FRAMES at a time and computes per-chunk
    RMS energy to detect speech and silence.

    State machine:
    - Pre-speech: chunks below ``silence_threshold`` are discarded so
      that leading silence is not fed to the transcriber.
    - Speech onset: first chunk at or above threshold starts recording.
    - During speech: every chunk is appended; once
      ``silence_duration_chunks`` consecutive sub-threshold chunks are
      seen the recording ends.
    - Safety cap: if MAX_RECORD_CHUNKS frames accumulate, recording
      stops regardless of silence to prevent unbounded capture.

    Args:
        silence_threshold: RMS value (int16 scale) below which a chunk
            is considered silent. Default DEFAULT_SILENCE_RMS (300).
        silence_duration_chunks: How many consecutive silent chunks end
            the recording. Default SILENCE_CHUNKS (10 = 1.0 s).

    Returns:
        A 1-D numpy array with dtype int16 at SAMPLE_RATE Hz.
        Returns ``np.zeros(0, dtype=np.int16)`` if no speech was
        detected before the recording stopped.

    Note (Phase 2 / stt.py):
        mic.py intentionally returns int16.  Convert before Moonshine::

            audio_float32 = audio_int16.astype(np.float32) / 32768.0
    """
    frames: list[np.ndarray] = []
    speech_started = False
    silent_count = 0
    total_chunks = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
    ) as stream:
        while True:
            chunk, _ = stream.read(CHUNK_FRAMES)
            total_chunks += 1
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

            if not speech_started:
                if rms >= silence_threshold:
                    speech_started = True
                    silent_count = 0
                    frames.append(chunk.copy())
                # Cap pre-speech wait at the same MAX_RECORD_CHUNKS limit
                elif total_chunks >= MAX_RECORD_CHUNKS:
                    break
            else:
                frames.append(chunk.copy())
                if rms < silence_threshold:
                    silent_count += 1
                    if silent_count >= silence_duration_chunks:
                        break
                else:
                    silent_count = 0

            if len(frames) >= MAX_RECORD_CHUNKS:
                break

    if not frames:
        return np.zeros(0, dtype=np.int16)

    return np.concatenate(frames, axis=0).flatten()
