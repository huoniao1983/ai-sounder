"""Douyin official live-interaction adapter."""

from __future__ import annotations

from typing import Any

from engine.platform.ws_adapter import JsonWebSocketAdapter


class DouyinLiveAdapter(JsonWebSocketAdapter):
    name = "douyin"
    default_type_map = {
        **JsonWebSocketAdapter.default_type_map,
        "WebcastChatMessage": "danmaku",
        "WebcastGiftMessage": "gift",
        "WebcastMemberMessage": "enter",
        "WebcastSocialMessage": "follow",
        "WebcastLikeMessage": "like",
    }

    def __init__(self) -> None:
        super().__init__()
        self.credentials: dict[str, Any] = {}

