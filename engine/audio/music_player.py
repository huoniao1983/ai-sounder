"""Sequential BGM playback backed by a decoder thread and pre-buffered PCM."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

import numpy as np


class MusicPlayer:
    """Read pre-decoded float32 chunks from a ring buffer.

    The audio callback only calls ``read``, so decoding stalls or track
    changes never block real-time mixing.
    """

    def __init__(
        self,
        volume: float = 0.35,
        sample_rate: int = 48000,
        channels: int = 2,
        min_buffer_blocks: int = 150,
        block_size: int = 960,
        decoder_factory: Callable[[list[str], int], None] | None = None,
    ) -> None:
        self.volume = volume
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.min_buffer_blocks = min_buffer_blocks
        self.playlist: list[str] = []
        self.idx = 0
        self._buffer: deque[np.ndarray] = deque()
        self._lock = threading.Lock()
        self._running = False
        self._decoder_thread: threading.Thread | None = None
        self._decoder_factory = decoder_factory

    def set_playlist(self, paths: list[str], start_index: int = 0) -> None:
        self.stop_decoder()
        self.playlist = list(paths)
        self.idx = max(0, min(start_index, len(paths) - 1)) if paths else 0
        self._buffer.clear()
        if not paths:
            return
        self._running = True
        decoder = self._decoder_factory or self._miniaudio_decoder
        self._decoder_thread = threading.Thread(target=self._decode_loop, args=(decoder,), daemon=True)
        self._decoder_thread.start()

    def enqueue_pcm(self, chunk: np.ndarray) -> None:
        chunk = np.asarray(chunk, dtype=np.float32)
        if chunk.ndim == 1:
            chunk = np.column_stack([chunk, chunk])
        if chunk.shape[1] != self.channels:
            chunk = np.repeat(chunk, self.channels, axis=1)[:, : self.channels]
        with self._lock:
            self._buffer.append(chunk * self.volume)

    def read(self, frames: int) -> np.ndarray:
        out = np.zeros((frames, self.channels), dtype=np.float32)
        filled = 0
        with self._lock:
            while self._buffer and filled < frames:
                chunk = self._buffer[0]
                take = min(len(chunk), frames - filled)
                out[filled : filled + take] = chunk[:take]
                if take < len(chunk):
                    self._buffer[0] = chunk[take:]
                else:
                    self._buffer.popleft()
                filled += take
        return out

    def skip_next(self) -> None:
        with self._lock:
            self._buffer.clear()
        if self.playlist:
            self.idx = (self.idx + 1) % len(self.playlist)
            self._restart_current_playlist()

    def stop_decoder(self) -> None:
        self._running = False
        if self._decoder_thread is not None:
            self._decoder_thread.join(timeout=1.0)
            self._decoder_thread = None

    def _restart_current_playlist(self) -> None:
        self.stop_decoder()
        if not self.playlist:
            return
        self._running = True
        decoder = self._decoder_factory or self._miniaudio_decoder
        self._decoder_thread = threading.Thread(target=self._decode_loop, args=(decoder,), daemon=True)
        self._decoder_thread.start()

    def _decode_loop(self, decoder: Callable[[list[str], int], None]) -> None:
        while self._running and self.playlist:
            try:
                decoder(self.playlist, self.idx)
            except Exception:
                pass
            finally:
                if self.playlist:
                    self.idx = (self.idx + 1) % len(self.playlist)

    def _miniaudio_decoder(self, paths: list[str], start_index: int) -> None:
        try:
            import miniaudio
        except ImportError as exc:
            raise RuntimeError("miniaudio is required: pip install 'aisounder-engine[audio]'") from exc
        path = paths[start_index]
        stream = miniaudio.stream_file(path, sample_rate=self.sample_rate, nchannels=self.channels)
        for pcm in stream:
            if not self._running:
                break
            sample = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
            while self._running and len(self._buffer) > self.min_buffer_blocks * 4:
                time.sleep(0.01)
            self.enqueue_pcm(sample)


__all__ = ["MusicPlayer"]
