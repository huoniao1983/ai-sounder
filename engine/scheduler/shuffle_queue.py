"""Weighted shuffle queue with cycle fairness and cross-cycle de-duplication."""

from __future__ import annotations

import random
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class ShuffleQueue(Generic[T]):
    """Return every item once per cycle without adjacent repeats.

    A whole shuffled cycle is the unit of fairness: each item appears exactly
    once before the deck is refilled, and the last item of one cycle is never
    equal to the first item of the next cycle.
    """

    def __init__(
        self,
        items: list[T],
        weights: Optional[list[float]] = None,
        seed: Optional[int] = None,
    ) -> None:
        if not items:
            raise ValueError("ShuffleQueue requires at least one item")
        if weights is not None and len(weights) != len(items):
            raise ValueError("items and weights must have the same length")
        self.items = list(items)
        self.weights = list(weights if weights is not None else [1.0] * len(items))
        if any(w <= 0 for w in self.weights):
            raise ValueError("all weights must be positive")
        self.rng = random.Random(seed)
        self.pool: list[T] = []
        self.last_played: Optional[T] = None
        self.cycle_count = 0

    def next(self) -> T:
        if not self.pool:
            self._refill()
        item = self.pool.pop()
        self.last_played = item
        return item

    def peek_next_prefetch(self) -> T:
        """Return the next item without consuming it, refilling if necessary."""

        if not self.pool:
            self._refill()
        return self.pool[-1]

    def peek_remaining(self) -> int:
        return len(self.pool)

    def update_items(
        self,
        items: list[T],
        weights: Optional[list[float]] = None,
    ) -> None:
        if not items:
            raise ValueError("at least one item is required")
        if weights is not None and len(weights) != len(items):
            raise ValueError("items and weights must have the same length")
        self.items = list(items)
        self.weights = list(weights if weights is not None else [1.0] * len(items))
        if any(w <= 0 for w in self.weights):
            raise ValueError("all weights must be positive")
        self.pool.clear()

    def _refill(self) -> None:
        if len(self.items) == 1:
            # Mathematically unavoidable; product layer enforces a longer pause.
            self.pool = [self.items[0]]
            self.cycle_count += 1
            return

        self.pool = self._weighted_shuffle(self.items, self.weights)
        self.cycle_count += 1
        if self.last_played is not None and self.pool[-1] == self.last_played:
            swap_idx = self.rng.randint(0, len(self.pool) - 2)
            self.pool[-1], self.pool[swap_idx] = self.pool[swap_idx], self.pool[-1]

    def _weighted_shuffle(self, items: list[T], weights: list[float]) -> list[T]:
        """Sample without replacement, weighting earlier slots more heavily."""

        remaining = list(zip(items, weights))
        result: list[T] = []
        while remaining:
            total = sum(w for _, w in remaining)
            threshold = self.rng.uniform(0.0, total)
            cumulative = 0.0
            for index, (item, weight) in enumerate(remaining):
                cumulative += weight
                if cumulative >= threshold:
                    result.append(item)
                    remaining.pop(index)
                    break
        # The queue pops from the tail, so reverse the weighted draw order:
        # items sampled first (higher weight) end up closer to the tail and
        # therefore play earlier.
        return list(reversed(result))


__all__ = ["ShuffleQueue"]
