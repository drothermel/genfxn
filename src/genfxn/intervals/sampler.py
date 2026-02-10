import random
from typing import TypeVar

from genfxn.core.trace import TraceStep, trace_step
from genfxn.intervals.models import (
    BoundaryMode,
    IntervalsAxes,
    IntervalsSpec,
    OperationType,
)

_TARGET_OPERATION_PREFS: dict[int, list[OperationType]] = {
    1: [OperationType.TOTAL_COVERAGE, OperationType.MERGED_COUNT],
    2: [
        OperationType.MERGED_COUNT,
        OperationType.TOTAL_COVERAGE,
        OperationType.MAX_OVERLAP_COUNT,
    ],
    3: [
        OperationType.MERGED_COUNT,
        OperationType.MAX_OVERLAP_COUNT,
        OperationType.GAP_COUNT,
    ],
    4: [OperationType.MAX_OVERLAP_COUNT, OperationType.GAP_COUNT],
    5: [OperationType.GAP_COUNT],
}

_TARGET_BOUNDARY_PREFS: dict[int, list[BoundaryMode]] = {
    1: [BoundaryMode.CLOSED_CLOSED],
    2: [
        BoundaryMode.CLOSED_OPEN,
        BoundaryMode.CLOSED_CLOSED,
        BoundaryMode.OPEN_CLOSED,
        BoundaryMode.OPEN_OPEN,
    ],
    3: [
        BoundaryMode.OPEN_CLOSED,
        BoundaryMode.CLOSED_OPEN,
        BoundaryMode.OPEN_OPEN,
    ],
    4: [BoundaryMode.OPEN_OPEN, BoundaryMode.OPEN_CLOSED],
    5: [
        BoundaryMode.OPEN_OPEN,
        BoundaryMode.CLOSED_OPEN,
        BoundaryMode.OPEN_CLOSED,
    ],
}

_TARGET_MERGE_TOUCHING_PREFS: dict[int, list[bool]] = {
    1: [False, True],
    2: [False, True],
    3: [True, False],
    4: [True, False],
    5: [True, False],
}

_TARGET_ENDPOINT_CLIP_ABS_RANGES: dict[int, tuple[int, int]] = {
    1: (14, 20),
    2: (10, 16),
    3: (7, 12),
    4: (5, 9),
    5: (3, 6),
}

T = TypeVar("T")


def _sample_int_in_range(
    value_range: tuple[int, int],
    rng: random.Random,
) -> int:
    return rng.randint(value_range[0], value_range[1])


def _sample_int_with_preferred_overlap(
    *,
    available: tuple[int, int],
    preferred: tuple[int, int],
    rng: random.Random,
) -> int:
    lo = max(available[0], preferred[0])
    hi = min(available[1], preferred[1])
    if lo <= hi:
        return rng.randint(lo, hi)
    return rng.randint(available[0], available[1])


def _sample_probability(
    prob_range: tuple[float, float], rng: random.Random
) -> float:
    return rng.uniform(prob_range[0], prob_range[1])


def _pick_from_preferred(
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
        endpoint_clip_abs = _sample_int_in_range(
            axes.endpoint_clip_abs_range,
            rng,
        )
        endpoint_quantize_step = _sample_int_in_range(
            axes.endpoint_quantize_step_range,
            rng,
        )
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
        endpoint_clip_abs = _sample_int_with_preferred_overlap(
            available=axes.endpoint_clip_abs_range,
            preferred=_TARGET_ENDPOINT_CLIP_ABS_RANGES[target_difficulty],
            rng=rng,
        )
        endpoint_quantize_step = _sample_int_in_range(
            axes.endpoint_quantize_step_range,
            rng,
        )

    allow_reversed_interval_prob = _sample_probability(
        axes.allow_reversed_interval_prob_range,
        rng,
    )
    degenerate_interval_prob = _sample_probability(
        axes.degenerate_interval_prob_range,
        rng,
    )
    nested_interval_prob = _sample_probability(
        axes.nested_interval_prob_range,
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
        "sample_endpoint_clip_abs",
        f"Endpoint clip abs: {endpoint_clip_abs}",
        endpoint_clip_abs,
    )
    trace_step(
        trace,
        "sample_endpoint_quantize_step",
        f"Endpoint quantize step: {endpoint_quantize_step}",
        endpoint_quantize_step,
    )
    trace_step(
        trace,
        "sample_reverse_prob",
        "Reversed interval probability sampled for query generation",
        allow_reversed_interval_prob,
    )
    trace_step(
        trace,
        "sample_degenerate_prob",
        "Degenerate interval probability sampled for query generation",
        degenerate_interval_prob,
    )
    trace_step(
        trace,
        "sample_nested_prob",
        "Nested interval probability sampled for query generation",
        nested_interval_prob,
    )

    return IntervalsSpec(
        operation=operation,
        boundary_mode=boundary_mode,
        merge_touching=merge_touching,
        endpoint_clip_abs=endpoint_clip_abs,
        endpoint_quantize_step=endpoint_quantize_step,
        allow_reversed_interval_prob=allow_reversed_interval_prob,
        degenerate_interval_prob=degenerate_interval_prob,
        nested_interval_prob=nested_interval_prob,
    )
