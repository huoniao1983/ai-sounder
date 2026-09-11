"""Configurable JSON WebSocket adapter for live platform event feeds."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import aiohttp

from engine.platform.base import DanmuEvent

LOGGER = logging.getLogger(__name__)


class JsonWebSocketAdapter:
    """Official WebSocket endpoint with configurable field mapping.

    Platforms differ in field names and authentication. Credentials therefore
    contain at least ``ws_url`` plus optional headers/query parameters and
    dotted JSON paths describing event type, user and content fields.
    """

    name = "websocket"
    default_type_map = {
        "danmaku": "danmaku",
        "comment": "danmaku",
        "chat": "danmaku",
        "gift": "gift",
        "enter": "enter",
        "member": "enter",
        "follow": "follow",
        "social": "follow",
        "like": "like",
    }

    def __init__(self) -> None:
        self.credentials: dict[str, Any] = {}
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None

    async def connect(self, credential: dict[str, Any]) -> None:
        ws_url = str(credential.get("ws_url", "")).strip()
        if not ws_url:
            raise ValueError(f"{self.name} 缺少 ws_url")
        self.credentials = dict(credential)
        headers = {str(key): str(value) for key, value in credential.get("headers", {}).items()}
        params = {str(key): str(value) for key, value in credential.get("params", {}).items()}
        if params:
            parsed = urlparse(ws_url)
            query = dict(parse_qsl(parsed.query))
            query.update(params)
            ws_url = urlunparse(parsed._replace(query=urlencode(query)))
        timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=None)
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        self._ws = await self._session.ws_connect(
            ws_url,
            heartbeat=float(credential.get("heartbeat", 20)),
        )

    async def disconnect(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def listen(self) -> AsyncIterator[DanmuEvent]:
        if self._ws is None:
            raise RuntimeError(f"{self.name} adapter is not connected")
        async for message in self._ws:
            if message.type == aiohttp.WSMsgType.TEXT:
                payload = self._decode(message.data)
            elif message.type == aiohttp.WSMsgType.BINARY:
                payload = self._decode(message.data)
            elif message.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                break
            else:
                continue
            if payload is None:
                continue
            event = self.normalize(payload)
            if event is not None:
                yield event

    def normalize(self, payload: dict[str, Any]) -> DanmuEvent | None:
        type_path = self.credentials.get("type_path", "type")
        raw_type = str(_get_path(payload, type_path) or "")
        event_type = self._event_type(raw_type)
        if event_type is None:
            return None
        user_path = self.credentials.get("user_path", "user")
        nickname_path = self.credentials.get("nickname_path", f"{user_path}.nickname")
        user_id_path = self.credentials.get("user_id_path", f"{user_path}.id")
        content_path = self.credentials.get("content_path", "content")
        gift_path = self.credentials.get("gift_count_path", "gift_count")
        nickname = str(_get_path(payload, nickname_path) or "观众")
        return DanmuEvent(
            platform=self.name,
            user_id=str(_get_path(payload, user_id_path) or ""),
            nickname=nickname,
            type=event_type,
            content=str(_get_path(payload, content_path) or ""),
            gift_count=int(_get_path(payload, gift_path) or 0),
            received_at=time.time(),
            raw=payload,
        )

    def _event_type(self, raw_type: str) -> str | None:
        mappings = {**self.default_type_map, **self.credentials.get("event_type_map", {})}
        if raw_type in mappings:
            return str(mappings[raw_type])
        lowered = raw_type.lower()
        for key, value in mappings.items():
            if key.lower() in lowered:
                return str(value)
        return None

    @staticmethod
    def _decode(raw: str | bytes) -> dict[str, Any] | None:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            LOGGER.debug("Ignoring non-JSON platform message")
            return None
        return payload if isinstance(payload, dict) else None


def _get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


__all__ = ["JsonWebSocketAdapter"]

