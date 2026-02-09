import random

from genfxn.core.trace import TraceStep, trace_step
from genfxn.intervals.models import IntervalsAxes, IntervalsSpec


def _sample_probability(
    prob_range: tuple[float, float], rng: random.Random
) -> float:
    return rng.uniform(prob_range[0], prob_range[1])


def sample_intervals_spec(
    axes: IntervalsAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> IntervalsSpec:
    if rng is None:
        rng = random.Random()

    operation = rng.choice(axes.operation_types)
    boundary_mode = rng.choice(axes.boundary_modes)
    merge_touching = rng.choice(axes.merge_touching_choices)

    trace_step(
        trace,
        "sample_operation",
        f"Operation: {operation.value}",
        operation.value,
    )
    trace_step(
        trace,
        "sample_boundary_mode",
        f"Boundary mode: {boundary_mode.value}",
        boundary_mode.value,
    )
    trace_step(
        trace,
        "sample_merge_touching",
        f"Merge touching: {merge_touching}",
        merge_touching,
    )
    trace_step(
        trace,
        "sample_reverse_prob",
        "Reversed interval probability sampled for query generation",
        _sample_probability(axes.allow_reversed_interval_prob_range, rng),
    )
    trace_step(
        trace,
        "sample_degenerate_prob",
        "Degenerate interval probability sampled for query generation",
        _sample_probability(axes.degenerate_interval_prob_range, rng),
    )
    trace_step(
        trace,
        "sample_nested_prob",
        "Nested interval probability sampled for query generation",
        _sample_probability(axes.nested_interval_prob_range, rng),
    )

    return IntervalsSpec(
        operation=operation,
        boundary_mode=boundary_mode,
        merge_touching=merge_touching,
    )
