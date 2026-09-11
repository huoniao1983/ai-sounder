"""Canonical event model and adapter interface shared by all platforms."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, AsyncIterator, Protocol


class EventType(StrEnum):
    DANMAKU = "danmaku"
    GIFT = "gift"
    ENTER = "enter"
    FOLLOW = "follow"
    LIKE = "like"


@dataclass(slots=True)
class DanmuEvent:
    platform: str
    user_id: str
    nickname: str
    type: EventType | str
    content: str = ""
    gift_count: int = 0
    received_at: float = field(default_factory=lambda: 0.0)
    raw: dict[str, Any] = field(default_factory=dict)


class PlatformAdapter(Protocol):
    name: str

    async def connect(self, credential: dict[str, Any]) -> None:
        ...

    async def disconnect(self) -> None:
        ...

    def listen(self) -> AsyncIterator[DanmuEvent]:
        ...

