import random

import pytest

from genfxn.core.sampling import intersect_ranges, pick_from_preferred
from genfxn.core.trace import TraceStep, trace_step


def test_intersect_ranges_overlap() -> None:
    assert intersect_ranges((1, 5), (3, 7)) == (3, 5)
    assert intersect_ranges((3, 7), (1, 5)) == (3, 5)


def test_intersect_ranges_disjoint() -> None:
    assert intersect_ranges((1, 3), (5, 7)) is None
    assert intersect_ranges((5, 7), (1, 3)) is None


def test_intersect_ranges_touching() -> None:
    assert intersect_ranges((1, 4), (4, 6)) == (4, 4)
    assert intersect_ranges((4, 6), (1, 4)) == (4, 4)


def test_intersect_ranges_contained() -> None:
    assert intersect_ranges((1, 10), (3, 5)) == (3, 5)
    assert intersect_ranges((3, 5), (1, 10)) == (3, 5)


def test_intersect_ranges_identical() -> None:
    assert intersect_ranges((3, 5), (3, 5)) == (3, 5)


def test_intersect_ranges_single_point() -> None:
    assert intersect_ranges((5, 5), (5, 5)) == (5, 5)


def test_intersect_ranges_negative() -> None:
    assert intersect_ranges((-5, -1), (-3, 2)) == (-3, -1)
    assert intersect_ranges((-3, 2), (-5, -1)) == (-3, -1)


def test_pick_from_preferred_uses_overlap() -> None:
    rng = random.Random(42)
    available = [1, 2, 3, 4]
    preferred = [9, 3, 2]
    result = pick_from_preferred(available, preferred, rng)
    assert result in {2, 3}


def test_pick_from_preferred_falls_back_to_available() -> None:
    rng = random.Random(42)
    available = ["a", "b", "c"]
    preferred = ["x", "y"]
    result = pick_from_preferred(available, preferred, rng)
    assert result in set(available)


def test_pick_from_preferred_rejects_empty_available() -> None:
    rng = random.Random(42)
    with pytest.raises(
        ValueError, match="available must contain at least one item"
    ):
        pick_from_preferred([], ["x"], rng)


def test_trace_step_appends_when_trace_is_present() -> None:
    trace: list[TraceStep] = []
    trace_step(trace, "sample", "picked value", {"k": 1})
    assert len(trace) == 1
    assert trace[0].step == "sample"
    assert trace[0].choice == "picked value"
    assert trace[0].value == {"k": 1}


def test_trace_step_is_noop_when_trace_is_none() -> None:
    trace_step(None, "sample", "picked value", 1)
