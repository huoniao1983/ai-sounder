"""Deterministic platform adapter used for development and end-to-end tests."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from engine.platform.base import DanmuEvent


class MockPlatformAdapter:
    name = "mock"

    def __init__(self, events: list[DanmuEvent] | None = None, replay: bool = False) -> None:
        self.events = list(events or self.default_events())
        self.replay = replay
        self.connected = False

    async def connect(self, credential: dict[str, Any] | None = None) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def listen(self) -> AsyncIterator[DanmuEvent]:
        if not self.connected:
            raise RuntimeError("mock adapter is not connected")
        while self.replay or self.events:
            for event in list(self.events):
                yield event
            if not self.replay:
                break

    @staticmethod
    def default_events() -> list[DanmuEvent]:
        now = time.time()
        return [
            DanmuEvent("mock", "u-1", "ok小李", "enter", received_at=now),
            DanmuEvent("mock", "u-2", "小雅", "danmaku", "这个多少钱？", received_at=now),
            DanmuEvent("mock", "u-3", "礼物哥", "gift", "大宝剑", gift_count=1, received_at=now),
            DanmuEvent("mock", "u-4", "正午晒太阳", "follow", received_at=now),
        ]

