"""Application-internal mixer: one voice channel plus one music channel."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from typing import Any

import numpy as np

from engine.audio.duck_controller import DuckController

MusicReader = Callable[[int], np.ndarray]


def _mono_float32(pcm: bytes | np.ndarray) -> np.ndarray:
    if isinstance(pcm, bytes):
        sample = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        sample = np.asarray(pcm)
        if np.issubdtype(sample.dtype, np.integer):
            sample = sample.astype(np.float32) / 32768.0
        else:
            sample = sample.astype(np.float32)
    if sample.ndim == 2:
        sample = sample.mean(axis=1)
    if sample.ndim != 1:
        sample = sample.reshape(-1)
    return sample


def _to_stereo(block: np.ndarray | None, frames: int) -> np.ndarray:
    if block is None:
        return np.zeros((frames, 2), dtype=np.float32)
    block = np.asarray(block, dtype=np.float32)
    if block.ndim == 1:
        block = np.column_stack([block, block])
    elif block.ndim != 2:
        block = block.reshape(-1, 1)
    if block.shape[1] == 1:
        block = np.repeat(block, 2, axis=1)
    if block.shape[0] < frames:
        block = np.vstack([block, np.zeros((frames - block.shape[0], block.shape[1]), dtype=np.float32)])
    return block[:frames]


class AudioMixer:
    """Mix voice and music into one stereo float32 stream.

    A PortAudio callback drives ``render_block`` at 20ms intervals; the
    callback must not block or allocate large objects.
    """

    def __init__(
        self,
        output_device_id: int | None = None,
        music_reader: MusicReader | None = None,
        sample_rate: int = 48000,
        block_size: int = 960,
        ducking_enabled: bool = True,
        normal_gain: float = 0.35,
        ducked_gain: float = 0.10,
    ) -> None:
        self.output_device_id = output_device_id
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.ducking_enabled = ducking_enabled
        self._music_reader = music_reader or (lambda frames: np.zeros((frames, 2), dtype=np.float32))
        self._duck = DuckController(normal_gain=normal_gain, ducked_gain=ducked_gain)
        self._voice_queue: deque[np.ndarray] = deque()
        self._lock = threading.Lock()
        self._stream: Any = None

    async def enqueue_voice(self, pcm_48k: bytes | np.ndarray, source: str = "") -> None:
        chunk = _mono_float32(pcm_48k)
        with self._lock:
            self._voice_queue.append(chunk)

    def render_block(self, frames: int | None = None, music: np.ndarray | None = None) -> np.ndarray:
        frames = frames or self.block_size
        voice = self._drain_voice(frames)
        if music is None:
            music = self._music_reader(frames)
        music = _to_stereo(music, frames)
        if self.ducking_enabled:
            music = music * self._duck.step(voice, frames)
        voice_stereo = np.column_stack([voice, voice])
        mixed = voice_stereo + music
        return np.tanh(mixed * 1.2) * 0.9

    def _drain_voice(self, frames: int) -> np.ndarray:
        out = np.zeros(frames, dtype=np.float32)
        filled = 0
        with self._lock:
            while self._voice_queue and filled < frames:
                chunk = self._voice_queue[0]
                take = min(len(chunk), frames - filled)
                out[filled : filled + take] = chunk[:take]
                if take < len(chunk):
                    self._voice_queue[0] = chunk[take:]
                else:
                    self._voice_queue.popleft()
                filled += take
        return out

    def start(self) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is required: pip install 'aisounder-engine[audio]'") from exc
        self._stream = sd.OutputStream(
            device=self.output_device_id,
            samplerate=self.sample_rate,
            channels=2,
            dtype="float32",
            blocksize=self.block_size,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, outdata: np.ndarray, frames: int, time_info: Any, status: Any) -> None:
        outdata[:] = self.render_block(frames)


__all__ = ["AudioMixer"]

