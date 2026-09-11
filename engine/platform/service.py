"""Thread-safe lifecycle manager for live platform adapters."""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from typing import Any

from engine.platform.douyin import DouyinLiveAdapter
from engine.platform.kuaishou import KuaishouLiveAdapter
from engine.platform.mock import MockPlatformAdapter


class PlatformService:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._adapters: dict[str, Any] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._events: deque[dict[str, Any]] = deque(maxlen=500)

    def connect(self, platform: str, config: dict[str, Any]) -> dict[str, Any]:
        return self._submit(self._connect(platform, config))

    def disconnect(self, platform: str) -> dict[str, Any]:
        return self._submit(self._disconnect(platform))

    def status(self) -> list[dict[str, Any]]:
        return [
            {"platform": name, "connected": name in self._adapters}
            for name in ("douyin", "kuaishou", "bilibili")
        ]

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._events)[-limit:]

    def ingest(self, platform: str, payload: dict[str, Any]) -> dict[str, Any]:
        adapter = self._create_adapter(platform)
        event = adapter.normalize(payload)
        if event is None:
            return {"accepted": False, "reason": "unsupported event"}
        self._events.append(
            {
                "platform": event.platform,
                "user_id": event.user_id,
                "nickname": event.nickname,
                "type": str(event.type),
                "content": event.content,
                "gift_count": event.gift_count,
                "received_at": event.received_at,
            }
        )
        return {"accepted": True, "type": str(event.type)}

    async def _connect(self, platform: str, config: dict[str, Any]) -> dict[str, Any]:
        await self._disconnect(platform)
        adapter = self._create_adapter(platform)
        await adapter.connect(config)
        self._adapters[platform] = adapter
        self._tasks[platform] = asyncio.create_task(self._pump(platform, adapter))
        return {"platform": platform, "connected": True}

    async def _disconnect(self, platform: str) -> dict[str, Any]:
        task = self._tasks.pop(platform, None)
        if task is not None:
            task.cancel()
        adapter = self._adapters.pop(platform, None)
        if adapter is not None:
            await adapter.disconnect()
        return {"platform": platform, "connected": False}

    async def _pump(self, platform: str, adapter: Any) -> None:
        try:
            async for event in adapter.listen():
                self._events.append(
                    {
                        "platform": event.platform,
                        "user_id": event.user_id,
                        "nickname": event.nickname,
                        "type": str(event.type),
                        "content": event.content,
                        "gift_count": event.gift_count,
                        "received_at": event.received_at,
                    }
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._events.append({"platform": platform, "type": "error", "content": str(exc)})
        finally:
            self._adapters.pop(platform, None)
            self._tasks.pop(platform, None)

    @staticmethod
    def _create_adapter(platform: str) -> Any:
        if platform == "douyin":
            return DouyinLiveAdapter()
        if platform == "kuaishou":
            return KuaishouLiveAdapter()
        if platform == "mock":
            return MockPlatformAdapter(replay=False)
        raise ValueError(f"Unsupported platform: {platform}")

    def _submit(self, coroutine: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result(timeout=30)


__all__ = ["PlatformService"]
