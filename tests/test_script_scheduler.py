import asyncio

from engine.scheduler.script_scheduler import Script, ScriptScheduler, ScriptSchedulerConfig


class FakeTTS:
    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay

    async def synthesize(self, content: str, voice_id: str) -> bytes:
        if self.delay:
            await asyncio.sleep(self.delay)
        return content.encode("utf-8")


class FakeMixer:
    def __init__(self) -> None:
        self.voice_items: list[tuple[bytes, str]] = []

    async def enqueue_voice(self, pcm: bytes, source: str) -> None:
        self.voice_items.append((pcm, source))


def test_scheduler_plays_without_adjacent_script_repeat() -> None:
    async def scenario() -> list[str]:
        scripts = [
            Script(id="a", content="a"),
            Script(id="b", content="b"),
            Script(id="c", content="c"),
        ]
        mixer = FakeMixer()
        scheduler = ScriptScheduler(
            scripts=scripts,
            voice_id="test",
            tts_engine=FakeTTS(),
            mixer=mixer,
            config=ScriptSchedulerConfig(min_gap_seconds=0.01, max_gap_seconds=0.02),
            random_seed=4,
        )

        async def stop_after_short_run() -> None:
            await asyncio.sleep(0.35)
            scheduler.stop()

        await asyncio.gather(scheduler.run(), stop_after_short_run())
        return [source.removeprefix("script:") for _, source in mixer.voice_items]

    ids = asyncio.run(scenario())
    assert len(ids) >= 6
    assert all(left != right for left, right in zip(ids, ids[1:]))


def test_prefetch_caches_upcoming_script() -> None:
    async def scenario() -> bool:
        scripts = [
            Script(id="a", content="alpha"),
            Script(id="b", content="beta"),
        ]
        mixer = FakeMixer()
        scheduler = ScriptScheduler(
            scripts=scripts,
            voice_id="test",
            tts_engine=FakeTTS(delay=0.0),
            mixer=mixer,
            config=ScriptSchedulerConfig(min_gap_seconds=0.001, max_gap_seconds=0.001),
            random_seed=8,
        )

        async def stop_soon() -> None:
            await asyncio.sleep(0.15)
            scheduler.stop()

        await asyncio.gather(scheduler.run(), stop_soon())
        return bool(scheduler._prefetched)

    assert asyncio.run(scenario())
