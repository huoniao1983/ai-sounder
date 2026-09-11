from statistics import mean

import pytest

from engine.scheduler.shuffle_queue import ShuffleQueue


def test_no_adjacent_repeat_over_many_plays() -> None:
    queue = ShuffleQueue(["A", "B", "C", "D"], seed=7)
    sequence = [queue.next() for _ in range(1000)]
    for left, right in zip(sequence, sequence[1:]):
        assert left != right


def test_every_item_appears_once_per_cycle() -> None:
    queue = ShuffleQueue(["A", "B", "C", "D"], seed=11)
    for _ in range(250):
        played = [queue.next() for _ in range(4)]
        assert sorted(played) == ["A", "B", "C", "D"]


def test_cross_cycle_boundary_never_repeats() -> None:
    queue = ShuffleQueue(["A", "B", "C"], seed=42)
    previous = queue.next()
    for _ in range(9999):
        current = queue.next()
        assert current != previous
        previous = current


def test_weighted_item_tends_to_play_earlier() -> None:
    queue = ShuffleQueue(["A", "B", "C", "D"], weights=[8, 1, 1, 1], seed=3)
    positions: list[int] = []
    for _ in range(500):
        cycle = [queue.next() for _ in range(4)]
        positions.append(cycle.index("A"))
    assert mean(positions) < 1.8


def test_two_items_alternate_without_repetition() -> None:
    queue = ShuffleQueue(["A", "B"], seed=5)
    sequence = [queue.next() for _ in range(500)]
    assert all(left != right for left, right in zip(sequence, sequence[1:]))


def test_single_item_is_allowed_but_repeats() -> None:
    queue = ShuffleQueue(["A"])
    assert [queue.next() for _ in range(3)] == ["A", "A", "A"]


def test_dynamic_update_keeps_last_played_guard() -> None:
    queue = ShuffleQueue(["A", "B", "C", "D"], seed=1)
    first = queue.next()
    queue.update_items([first, "X", "Y"], weights=[1, 3, 3])
    second = queue.next()
    assert second != first


def test_peek_does_not_consume() -> None:
    queue = ShuffleQueue(["A", "B", "C"], seed=2)
    next_item = queue.peek_next_prefetch()
    assert next_item == queue.next()


def test_empty_items_rejected() -> None:
    with pytest.raises(ValueError):
        ShuffleQueue([])
