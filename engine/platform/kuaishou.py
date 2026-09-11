"""Kuaishou open-platform live-interaction adapter."""

from __future__ import annotations

from typing import Any

from engine.platform.ws_adapter import JsonWebSocketAdapter


class KuaishouLiveAdapter(JsonWebSocketAdapter):
    name = "kuaishou"
    default_type_map = {
        **JsonWebSocketAdapter.default_type_map,
        "COMMENT": "danmaku",
        "GIFT": "gift",
        "ENTER_ROOM": "enter",
        "FOLLOW": "follow",
        "LIKE": "like",
    }

    def __init__(self) -> None:
        super().__init__()
        self.credentials: dict[str, Any] = {}

