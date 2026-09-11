import asyncio

from engine.platform.mock import MockPlatformAdapter


def test_mock_adapter_emits_deterministic_events() -> None:
    adapter = MockPlatformAdapter()

    async def collect() -> list[str]:
        await adapter.connect()
        return [event.nickname async for event in adapter.listen()]

    nicknames = asyncio.run(collect())
    assert nicknames == ["ok小李", "小雅", "礼物哥", "正午晒太阳"]

