import random

from genfxn.core.sampling import sample_probability
from genfxn.core.trace import TraceStep, trace_step
from genfxn.intervals.models import (
    IntervalsAxes,
    IntervalsSpec,
)


def _sample_int_in_range(
    value_range: tuple[int, int],
    rng: random.Random,
) -> int:
    return rng.randint(value_range[0], value_range[1])


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
    endpoint_clip_abs = _sample_int_in_range(axes.endpoint_clip_abs_range, rng)
    endpoint_quantize_step = _sample_int_in_range(
        axes.endpoint_quantize_step_range,
        rng,
    )
    allow_reversed_interval_prob = sample_probability(
        axes.allow_reversed_interval_prob_range,
        rng,
    )
    degenerate_interval_prob = sample_probability(
        axes.degenerate_interval_prob_range,
        rng,
    )
    nested_interval_prob = sample_probability(
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
