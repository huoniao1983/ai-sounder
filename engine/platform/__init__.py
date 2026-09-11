"""Platform adapter abstractions, official feeds and deterministic mocks."""

from engine.platform.base import DanmuEvent, PlatformAdapter
from engine.platform.douyin import DouyinLiveAdapter
from engine.platform.kuaishou import KuaishouLiveAdapter
from engine.platform.mock import MockPlatformAdapter
from engine.platform.service import PlatformService

__all__ = [
    "DanmuEvent",
    "DouyinLiveAdapter",
    "KuaishouLiveAdapter",
    "MockPlatformAdapter",
    "PlatformAdapter",
    "PlatformService",
]
