"""Asynchronous main-script playback loop with pre-synthesis caching."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Optional

from engine.scheduler.shuffle_queue import ShuffleQueue

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class Script:
    id: str
    content: str
    weight: float = 1.0
    enabled: bool = True
    instruction: str = ""
    ssml: str = ""


@dataclass(slots=True)
class ScriptSchedulerConfig:
    min_gap_seconds: float = 3.0
    max_gap_seconds: float = 8.0
    prefetch_timeout_seconds: float = 10.0
    interrupt_mode: str = "queue"


class ScriptScheduler:
    """Play scripts through a single voice channel with human-like pauses.

    Interactions share the same voice channel at the mixer level, so the
    scheduler never needs to reason about simultaneous speech.
    """

    def __init__(
        self,
        scripts: list[Script],
        voice_id: str,
        tts_engine: Any,
        mixer: Any,
        config: Optional[ScriptSchedulerConfig] = None,
        random_seed: Optional[int] = None,
        on_script_played: Optional[Callable[[Script, int, int, float], None]] = None,
    ) -> None:
        self.scripts = list(scripts)
        self.voice_id = voice_id
        self.tts_engine = tts_engine
        self.mixer = mixer
        self.config = config or ScriptSchedulerConfig()
        self.on_script_played = on_script_played
        self.queue = self._build_queue(random_seed)
        self.rng = random.Random(random_seed)
        self.running = False
        self.current_script: Optional[Script] = None
        self._prefetched: dict[str, Any] = {}
        self._prefetch_tasks: set[asyncio.Task[Any]] = set()

    def _build_queue(self, seed: Optional[int]) -> ShuffleQueue[Script]:
        enabled = [s for s in self.scripts if s.enabled]
        return ShuffleQueue(
            enabled,
            weights=[s.weight for s in enabled],
            seed=seed,
        )

    async def run(self) -> None:
        if self.running:
            raise RuntimeError("scheduler is already running")
        self.running = True
        while self.running:
            try:
                script = self.queue.next()
            except ValueError:
                LOGGER.warning("no enabled scripts; waiting for update")
                await asyncio.sleep(1.0)
                continue

            self.current_script = script
            audio = self._prefetched.pop(script.id, None)
            if audio is None:
                audio = await self._synthesize(script)
                if audio is None:
                    LOGGER.warning("skipping script %s after synthesis failure", script.id)
                    continue

            await self.mixer.enqueue_voice(audio, source=f"script:{script.id}")

            next_script = self.queue.peek_next_prefetch()
            if next_script.id not in self._prefetched:
                task = asyncio.create_task(self._prefetch(next_script))
                self._prefetch_tasks.add(task)
                task.add_done_callback(self._prefetch_tasks.discard)

            gap = self._gap_seconds()
            self.queue_pos = max(self.queue.peek_remaining(), 0)
            if self.on_script_played is not None:
                self.on_script_played(
                    script,
                    self.queue.cycle_count,
                    self.queue.peek_remaining(),
                    gap,
                )
            await asyncio.sleep(gap)
        self.current_script = None

    def update_scripts(self, scripts: list[Script]) -> None:
        self.scripts = list(scripts)
        enabled = [s for s in self.scripts if s.enabled]
        self.queue.update_items(
            enabled,
            weights=[s.weight for s in enabled],
        )
        # Stale cache keys are harmless: unused entries are simply replaced.
        self._prefetched = {}

    def stop(self) -> None:
        self.running = False

    def state(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "current_script_id": self.current_script.id if self.current_script else None,
            "pool_remaining": self.queue.peek_remaining(),
            "cycle_no": self.queue.cycle_count,
            "enabled_count": sum(1 for s in self.scripts if s.enabled),
        }

    def _gap_seconds(self) -> float:
        enabled_count = sum(1 for s in self.scripts if s.enabled)
        if enabled_count == 1:
            # PRD: N=1 repeats inevitably, so require at least 10s between plays.
            return max(self.rng.uniform(self.config.min_gap_seconds, self.config.max_gap_seconds), 10.0)
        return self.rng.uniform(self.config.min_gap_seconds, self.config.max_gap_seconds)

    async def _prefetch(self, script: Script) -> None:
        if script.id in self._prefetched:
            return
        audio = await self._synthesize(script)
        if audio is not None:
            self._prefetched[script.id] = audio

    async def _synthesize(self, script: Script) -> Any:
        try:
            try:
                call = self.tts_engine.synthesize(
                    script.content,
                    self.voice_id,
                    instruction=script.instruction,
                    ssml=script.ssml,
                )
            except TypeError:
                call = self.tts_engine.synthesize(script.content, self.voice_id)
            return await asyncio.wait_for(call, timeout=self.config.prefetch_timeout_seconds)
        except asyncio.TimeoutError:
            LOGGER.warning("TTS timeout for script %s", script.id)
        except Exception:
            LOGGER.exception("TTS failed for script %s", script.id)
        return None


__all__ = ["Script", "ScriptScheduler", "ScriptSchedulerConfig"]
