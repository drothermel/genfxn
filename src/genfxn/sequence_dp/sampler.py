import random
from typing import TypeVar

from genfxn.core.trace import TraceStep, trace_step
from genfxn.sequence_dp.models import (
    OutputMode,
    PredicateAbsDiffLe,
    PredicateEq,
    PredicateModEq,
    PredicateType,
    SequenceDpAxes,
    SequenceDpSpec,
    TemplateType,
    TieBreakOrder,
)

_TARGET_TEMPLATE_PREFS: dict[int, list[TemplateType]] = {
    1: [TemplateType.GLOBAL],
    2: [TemplateType.GLOBAL],
    3: [TemplateType.GLOBAL, TemplateType.LOCAL],
    4: [TemplateType.LOCAL, TemplateType.GLOBAL],
    5: [TemplateType.LOCAL],
}

_TARGET_OUTPUT_PREFS: dict[int, list[OutputMode]] = {
    1: [OutputMode.SCORE],
    2: [OutputMode.SCORE, OutputMode.ALIGNMENT_LEN],
    3: [OutputMode.ALIGNMENT_LEN, OutputMode.SCORE, OutputMode.GAP_COUNT],
    4: [OutputMode.GAP_COUNT, OutputMode.ALIGNMENT_LEN, OutputMode.SCORE],
    5: [OutputMode.GAP_COUNT, OutputMode.ALIGNMENT_LEN],
}

_TARGET_PREDICATE_PREFS: dict[int, list[PredicateType]] = {
    1: [PredicateType.EQ],
    2: [PredicateType.EQ, PredicateType.ABS_DIFF_LE],
    3: [PredicateType.ABS_DIFF_LE, PredicateType.EQ, PredicateType.MOD_EQ],
    4: [PredicateType.MOD_EQ, PredicateType.ABS_DIFF_LE, PredicateType.EQ],
    5: [PredicateType.MOD_EQ, PredicateType.ABS_DIFF_LE],
}

_TARGET_TIE_BREAK_PREFS: dict[int, list[TieBreakOrder]] = {
    1: [TieBreakOrder.DIAG_UP_LEFT],
    2: [TieBreakOrder.DIAG_LEFT_UP, TieBreakOrder.DIAG_UP_LEFT],
    3: [
        TieBreakOrder.UP_DIAG_LEFT,
        TieBreakOrder.LEFT_DIAG_UP,
        TieBreakOrder.DIAG_UP_LEFT,
    ],
    4: [
        TieBreakOrder.UP_LEFT_DIAG,
        TieBreakOrder.LEFT_UP_DIAG,
        TieBreakOrder.UP_DIAG_LEFT,
    ],
    5: [TieBreakOrder.LEFT_UP_DIAG, TieBreakOrder.UP_LEFT_DIAG],
}

_TARGET_LEN_A: dict[int, tuple[int, int]] = {
    1: (1, 4),
    2: (2, 6),
    3: (4, 9),
    4: (6, 12),
    5: (8, 15),
}

_TARGET_LEN_B: dict[int, tuple[int, int]] = {
    1: (1, 4),
    2: (2, 6),
    3: (4, 9),
    4: (6, 12),
    5: (8, 15),
}

_TARGET_MATCH_SCORE: dict[int, tuple[int, int]] = {
    1: (2, 5),
    2: (2, 6),
    3: (1, 6),
    4: (1, 7),
    5: (1, 8),
}

_TARGET_MISMATCH_SCORE: dict[int, tuple[int, int]] = {
    1: (-2, 0),
    2: (-3, 0),
    3: (-4, 1),
    4: (-5, 1),
    5: (-6, 2),
}

_TARGET_GAP_SCORE: dict[int, tuple[int, int]] = {
    1: (-2, -1),
    2: (-3, -1),
    3: (-4, 0),
    4: (-5, 0),
    5: (-6, 1),
}

_TARGET_ABS_DIFF: dict[int, tuple[int, int]] = {
    1: (0, 1),
    2: (0, 2),
    3: (1, 3),
    4: (1, 4),
    5: (2, 6),
}

_TARGET_DIVISOR: dict[int, tuple[int, int]] = {
    1: (2, 4),
    2: (2, 6),
    3: (2, 8),
    4: (3, 10),
    5: (4, 12),
}

T = TypeVar("T")


def _intersect_ranges(
    a: tuple[int, int], b: tuple[int, int]
) -> tuple[int, int] | None:
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if lo > hi:
        return None
    return (lo, hi)


def _pick_from_preferred(
    available: list[T], preferred: list[T], rng: random.Random
) -> T:
    preferred_available = [value for value in preferred if value in available]
    if preferred_available:
        return rng.choice(preferred_available)
    return rng.choice(available)


def _pick_targeted_int(
    base_range: tuple[int, int],
    target_range: tuple[int, int],
    rng: random.Random,
) -> int:
    bounded = _intersect_ranges(base_range, target_range)
    if bounded is None:
        return rng.randint(*base_range)
    return rng.randint(*bounded)


def _sample_match_predicate(
    predicate_type: PredicateType,
    axes: SequenceDpAxes,
    target_difficulty: int | None,
    rng: random.Random,
) -> PredicateEq | PredicateAbsDiffLe | PredicateModEq:
    if predicate_type == PredicateType.EQ:
        return PredicateEq()

    if predicate_type == PredicateType.ABS_DIFF_LE:
        if target_difficulty is None:
            max_diff = rng.randint(*axes.abs_diff_range)
        else:
            max_diff = _pick_targeted_int(
                axes.abs_diff_range,
                _TARGET_ABS_DIFF[target_difficulty],
                rng,
            )
        return PredicateAbsDiffLe(max_diff=max_diff)

    if target_difficulty is None:
        divisor = rng.randint(*axes.divisor_range)
    else:
        divisor = _pick_targeted_int(
            axes.divisor_range,
            _TARGET_DIVISOR[target_difficulty],
            rng,
        )
    remainder = rng.randint(0, divisor - 1)
    return PredicateModEq(divisor=divisor, remainder=remainder)


def sample_sequence_dp_spec(
    axes: SequenceDpAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> SequenceDpSpec:
    if rng is None:
        rng = random.Random()

    target_difficulty = axes.target_difficulty

    if target_difficulty is None:
        template = rng.choice(axes.templates)
        output_mode = rng.choice(axes.output_modes)
        predicate_type = rng.choice(axes.predicate_types)
        len_a = rng.randint(*axes.len_a_range)
        len_b = rng.randint(*axes.len_b_range)
        tie_break = rng.choice(axes.tie_break_orders)
        match_score = rng.randint(*axes.match_score_range)
        mismatch_score = rng.randint(*axes.mismatch_score_range)
        gap_score = rng.randint(*axes.gap_score_range)
    else:
        template = _pick_from_preferred(
            axes.templates,
            _TARGET_TEMPLATE_PREFS[target_difficulty],
            rng,
        )
        output_mode = _pick_from_preferred(
            axes.output_modes,
            _TARGET_OUTPUT_PREFS[target_difficulty],
            rng,
        )
        predicate_type = _pick_from_preferred(
            axes.predicate_types,
            _TARGET_PREDICATE_PREFS[target_difficulty],
            rng,
        )
        tie_break = _pick_from_preferred(
            axes.tie_break_orders,
            _TARGET_TIE_BREAK_PREFS[target_difficulty],
            rng,
        )
        len_a = _pick_targeted_int(
            axes.len_a_range, _TARGET_LEN_A[target_difficulty], rng
        )
        len_b = _pick_targeted_int(
            axes.len_b_range, _TARGET_LEN_B[target_difficulty], rng
        )
        match_score = _pick_targeted_int(
            axes.match_score_range,
            _TARGET_MATCH_SCORE[target_difficulty],
            rng,
        )
        mismatch_score = _pick_targeted_int(
            axes.mismatch_score_range,
            _TARGET_MISMATCH_SCORE[target_difficulty],
            rng,
        )
        gap_score = _pick_targeted_int(
            axes.gap_score_range,
            _TARGET_GAP_SCORE[target_difficulty],
            rng,
        )

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

    match_predicate = _sample_match_predicate(
        predicate_type,
        axes,
        target_difficulty,
        rng,
    )
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
