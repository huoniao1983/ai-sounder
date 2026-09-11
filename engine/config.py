"""Runtime configuration for the Python engine sidecar."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class EngineConfig:
    db_url: str = "sqlite:///aisounder.db"
    output_device_id: int | None = None
    sample_rate: int = 48000
    block_size: int = 960
    min_gap_seconds: float = 3.0
    max_gap_seconds: float = 8.0
    interrupt_mode: str = "queue"
    bgm_volume: float = 0.35
    ducking_enabled: bool = True
    extra: dict = field(default_factory=dict)

    @classmethod
    def default_db_path(cls) -> Path:
        return Path("aisounder.db")

