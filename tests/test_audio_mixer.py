import asyncio

import numpy as np

from engine.audio.mixer import AudioMixer


def test_mixer_drains_voice_and_supplies_stereo() -> None:
    mixer = AudioMixer(ducking_enabled=False)
    tone = (np.sin(np.linspace(0, 10, 1920)) * 0.2).astype(np.float32)
    asyncio.run(mixer.enqueue_voice(tone))
    out = mixer.render_block(frames=960)
    assert out.shape == (960, 2)
    assert float(np.max(np.abs(out))) > 0.1
    assert float(np.max(np.abs(out))) <= 0.9


def test_soft_limiter_never_exceeds_full_scale() -> None:
    mixer = AudioMixer(ducking_enabled=False)
    music = np.full((100, 2), 2.0, dtype=np.float32)
    out = mixer.render_block(frames=100, music=music)
    assert float(np.max(np.abs(out))) <= 0.9

