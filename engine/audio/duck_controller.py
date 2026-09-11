"""Gain envelope that ducks background music while speech is active."""

from __future__ import annotations

import math

import numpy as np


class DuckController:
    """First-order smoothing gain controller.

    ``attack_ms`` controls how quickly music drops while voice is present and
    ``release_ms`` controls how quickly it returns to the normal level after
    silence. Calling ``step`` once per 20ms audio block matches the PRD
    real-time callback cadence.
    """

    def __init__(
        self,
        normal_gain: float = 0.35,
        ducked_gain: float = 0.10,
        attack_ms: float = 150.0,
        release_ms: float = 350.0,
        silence_threshold: float = 0.02,
        block_duration_ms: float = 20.0,
        release_delay_ms: float = 0.0,
    ) -> None:
        self.normal_gain = normal_gain
        self.ducked_gain = ducked_gain
        self.silence_threshold = silence_threshold
        self.block_duration_ms = block_duration_ms
        self.release_delay_blocks = int(release_delay_ms / block_duration_ms)
        self.attack_alpha = 1.0 - math.exp(-block_duration_ms / attack_ms)
        self.release_alpha = 1.0 - math.exp(-block_duration_ms / release_ms)
        self.gain = normal_gain
        self._silent_blocks = 0

    def step(self, voice_block: np.ndarray, frames: int = 0) -> float:
        block = np.asarray(voice_block, dtype=np.float32)
        energy = float(np.sqrt(np.mean(block**2))) if block.size else 0.0
        if energy > self.silence_threshold:
            self._silent_blocks = 0
            self.gain += (self.ducked_gain - self.gain) * self.attack_alpha
        else:
            self._silent_blocks += 1
            if self._silent_blocks > self.release_delay_blocks:
                self.gain += (self.normal_gain - self.gain) * self.release_alpha
        return self.gain


__all__ = ["DuckController"]

