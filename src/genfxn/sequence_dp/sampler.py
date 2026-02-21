import random

from genfxn.core.trace import TraceStep, trace_step
from genfxn.sequence_dp.models import (
    PredicateAbsDiffLe,
    PredicateEq,
    PredicateModEq,
    PredicateType,
    SequenceDpAxes,
    SequenceDpSpec,
)


def _sample_match_predicate(
    predicate_type: PredicateType,
    axes: SequenceDpAxes,
    rng: random.Random,
) -> PredicateEq | PredicateAbsDiffLe | PredicateModEq:
    if predicate_type == PredicateType.EQ:
        return PredicateEq()
    if predicate_type == PredicateType.ABS_DIFF_LE:
        return PredicateAbsDiffLe(max_diff=rng.randint(*axes.abs_diff_range))
    if predicate_type == PredicateType.MOD_EQ:
        divisor = rng.randint(*axes.divisor_range)
        remainder = rng.randint(0, divisor - 1)
        return PredicateModEq(divisor=divisor, remainder=remainder)
    raise ValueError(f"Unknown predicate type: {predicate_type.value}")


def sample_sequence_dp_spec(
    axes: SequenceDpAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> SequenceDpSpec:
    if rng is None:
        rng = random.Random()

    template = rng.choice(axes.templates)
    output_mode = rng.choice(axes.output_modes)
    predicate_type = rng.choice(axes.predicate_types)
    len_a = rng.randint(*axes.len_a_range)
    len_b = rng.randint(*axes.len_b_range)
    tie_break = rng.choice(axes.tie_break_orders)
    match_score = rng.randint(*axes.match_score_range)
    mismatch_score = rng.randint(*axes.mismatch_score_range)
    gap_score = rng.randint(*axes.gap_score_range)

    trace_step(
        trace,
        "sample_template",
        f"Template: {template.value}",
        template.value,
    )
    trace_step(
        trace,
        "sample_output_mode",
        f"Output mode: {output_mode.value}",
        output_mode.value,
    )
    trace_step(
        trace,
        "sample_predicate_type",
        f"Predicate type: {predicate_type.value}",
        predicate_type.value,
    )
    trace_step(trace, "sample_len_a", f"Length A: {len_a}", len_a)
    trace_step(trace, "sample_len_b", f"Length B: {len_b}", len_b)
    trace_step(
        trace,
        "sample_tie_break",
        f"Tie break: {tie_break.value}",
        tie_break.value,
    )
    trace_step(
        trace,
        "sample_match_score",
        f"Match score: {match_score}",
        match_score,
    )
    trace_step(
        trace,
        "sample_mismatch_score",
        f"Mismatch score: {mismatch_score}",
        mismatch_score,
    )
    trace_step(
        trace,
        "sample_gap_score",
        f"Gap score: {gap_score}",
        gap_score,
    )

    match_predicate = _sample_match_predicate(predicate_type, axes, rng)
    trace_step(
        trace,
        "sample_match_predicate",
        f"Match predicate: {match_predicate.kind}",
        match_predicate.model_dump(),
    )

    # Lengths shape query generation and future parity harnesses. They are not
    # part of the core spec at M0, so we only trace them for observability.
    _ = (len_a, len_b)

    return SequenceDpSpec(
        template=template,
        output_mode=output_mode,
        match_predicate=match_predicate,
        match_score=match_score,
        mismatch_score=mismatch_score,
        gap_score=gap_score,
        step_tie_break=tie_break,
    )
