import random

from genfxn.core.sampling import pick_from_preferred
from genfxn.core.trace import TraceStep, trace_step


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


def test_trace_step_appends_when_trace_is_present() -> None:
    trace: list[TraceStep] = []
    trace_step(trace, "sample", "picked value", {"k": 1})
    assert len(trace) == 1
    assert trace[0].step == "sample"
    assert trace[0].choice == "picked value"
    assert trace[0].value == {"k": 1}


def test_trace_step_is_noop_when_trace_is_none() -> None:
    trace_step(None, "sample", "picked value", 1)
