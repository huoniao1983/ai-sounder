import numpy as np

from engine.audio.duck_controller import DuckController


def _block(samples: int, amplitude: float) -> np.ndarray:
    t = np.arange(samples) / 48000.0
    return (np.sin(2 * np.pi * 1000 * t) * amplitude).astype(np.float32)


def test_ducking_reaches_target_within_500ms() -> None:
    controller = DuckController(attack_ms=150, release_ms=350)
    voice = _block(960, amplitude=0.5)
    for _ in range(25):  # 25 x 20ms = 500ms
        gain = controller.step(voice)
    assert abs(gain - 0.10) < 0.02


def test_gain_recovers_within_1500ms() -> None:
    controller = DuckController(attack_ms=150, release_ms=350)
    voice = _block(960, amplitude=0.5)
    silence = np.zeros(960, dtype=np.float32)
    for _ in range(25):
        controller.step(voice)
    for _ in range(75):  # 75 x 20ms = 1500ms
        gain = controller.step(silence)
    assert abs(gain - 0.35) < 0.02


def test_silence_keeps_normal_gain() -> None:
    controller = DuckController()
    silence = np.zeros(960, dtype=np.float32)
    for _ in range(20):
        gain = controller.step(silence)
    assert gain == 0.35

