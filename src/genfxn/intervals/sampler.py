import random

from genfxn.core.trace import TraceStep, trace_step
from genfxn.intervals.models import (
    BoundaryMode,
    IntervalsAxes,
    IntervalsSpec,
    OperationType,
)

_TARGET_OPERATION_PREFS: dict[int, list[OperationType]] = {
    1: [OperationType.TOTAL_COVERAGE],
    2: [OperationType.MERGED_COUNT, OperationType.TOTAL_COVERAGE],
    3: [OperationType.MERGED_COUNT, OperationType.MAX_OVERLAP_COUNT],
    4: [OperationType.MAX_OVERLAP_COUNT, OperationType.GAP_COUNT],
    5: [OperationType.GAP_COUNT],
}

_TARGET_BOUNDARY_PREFS: dict[int, list[BoundaryMode]] = {
    1: [BoundaryMode.CLOSED_CLOSED],
    2: [BoundaryMode.CLOSED_OPEN, BoundaryMode.CLOSED_CLOSED],
    3: [BoundaryMode.OPEN_CLOSED, BoundaryMode.CLOSED_OPEN],
    4: [BoundaryMode.OPEN_OPEN, BoundaryMode.OPEN_CLOSED],
    5: [BoundaryMode.OPEN_OPEN],
}

_TARGET_MERGE_TOUCHING_PREFS: dict[int, list[bool]] = {
    1: [False],
    2: [False, True],
    3: [True, False],
    4: [True],
    5: [True],
}


def _sample_probability(
    prob_range: tuple[float, float], rng: random.Random
) -> float:
    return rng.uniform(prob_range[0], prob_range[1])


def _pick_from_preferred[T](
    available: list[T], preferred: list[T], rng: random.Random
) -> T:
    preferred_available = [value for value in preferred if value in available]
    if preferred_available:
        return rng.choice(preferred_available)
    return rng.choice(available)


def sample_intervals_spec(
    axes: IntervalsAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> IntervalsSpec:
    if rng is None:
        rng = random.Random()

    target_difficulty = axes.target_difficulty

    if target_difficulty is None:
        operation = rng.choice(axes.operation_types)
        boundary_mode = rng.choice(axes.boundary_modes)
        merge_touching = rng.choice(axes.merge_touching_choices)
    else:
        operation = _pick_from_preferred(
            axes.operation_types,
            _TARGET_OPERATION_PREFS[target_difficulty],
            rng,
        )
        boundary_mode = _pick_from_preferred(
            axes.boundary_modes,
            _TARGET_BOUNDARY_PREFS[target_difficulty],
            rng,
        )
        merge_touching = _pick_from_preferred(
            axes.merge_touching_choices,
            _TARGET_MERGE_TOUCHING_PREFS[target_difficulty],
            rng,
        )

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
