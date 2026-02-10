import random

from genfxn.core.int32 import INT32_MAX, INT32_MIN, wrap_i32
from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.core.predicates import (
    Predicate,
    PredicateAnd,
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateNot,
    PredicateOdd,
    PredicateOr,
    eval_predicate,
)
from genfxn.core.query_utils import find_satisfying
from genfxn.stateful.eval import eval_stateful
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulAxes,
    StatefulSpec,
    ToggleSumSpec,
)


def _get_predicate_info(spec: StatefulSpec) -> Predicate:
    match spec:
        case ConditionalLinearSumSpec(predicate=p):
            return p
        case ResettingBestPrefixSumSpec(reset_predicate=p):
            return p
        case LongestRunSpec(match_predicate=p):
            return p
        case ToggleSumSpec(toggle_predicate=p):
            return p


def _make_matching_value(
    pred,
    value_range: tuple[int, int],
    rng: random.Random,
    *,
    int32_wrap: bool,
) -> int | None:
    lo, hi = value_range

    def _random_parity(start: int, step: int) -> int | None:
        if start > hi:
            return None
        slots = ((hi - start) // step) + 1
        return start + step * rng.randrange(slots)

    def _random_mod_eq(divisor: int, remainder: int) -> int | None:
        if divisor <= 0:
            return None
        if not int32_wrap:
            target = remainder % divisor
            first = lo + ((target - (lo % divisor)) % divisor)
            if first > hi:
                return None
            slots = ((hi - first) // divisor) + 1
            return first + divisor * rng.randrange(slots)

        int32_cycle = 1 << 32

        # Split [lo, hi] into int32 wrap segments and solve congruence per
        # segment: (x - k*2^32) % divisor == remainder.
        k_min = -((-(lo - INT32_MAX)) // int32_cycle)
        k_max = (hi - INT32_MIN) // int32_cycle
        if k_min > k_max:
            return None

        segments: list[tuple[int, int]] = []
        total_slots = 0
        for k in range(k_min, k_max + 1):
            seg_lo = max(lo, INT32_MIN + k * int32_cycle)
            seg_hi = min(hi, INT32_MAX + k * int32_cycle)
            if seg_lo > seg_hi:
                continue
            target = (remainder + ((k * int32_cycle) % divisor)) % divisor
            first = seg_lo + ((target - (seg_lo % divisor)) % divisor)
            if first > seg_hi:
                continue
            slots = ((seg_hi - first) // divisor) + 1
            segments.append((first, slots))
            total_slots += slots

        if total_slots == 0:
            return None

        pick = rng.randrange(total_slots)
        for first, slots in segments:
            if pick < slots:
                return first + divisor * pick
            pick -= slots
        return None

    match pred:
        case PredicateEven():
            first = lo if lo % 2 == 0 else lo + 1
            return _random_parity(first, 2)
        case PredicateOdd():
            first = lo if lo % 2 == 1 else lo + 1
            return _random_parity(first, 2)
        case PredicateLt(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if lo <= v_cmp - 1:
                return rng.randint(lo, min(v_cmp - 1, hi))
            return None
        case PredicateLe(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if lo <= v_cmp:
                return rng.randint(lo, min(v_cmp, hi))
            return None
        case PredicateGt(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if v_cmp + 1 <= hi:
                return rng.randint(max(v_cmp + 1, lo), hi)
            return None
        case PredicateGe(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if v_cmp <= hi:
                return rng.randint(max(v_cmp, lo), hi)
            return None
        case PredicateModEq(divisor=d, remainder=r):
            return _random_mod_eq(d, r)
        case PredicateNot() | PredicateAnd() | PredicateOr():
            return find_satisfying(
                lambda: rng.randint(lo, hi),
                lambda v: eval_predicate(pred, v, int32_wrap=int32_wrap),
            )
        case _:
            return rng.randint(lo, hi)


def _make_non_matching_value(
    pred,
    value_range: tuple[int, int],
    rng: random.Random,
    *,
    int32_wrap: bool,
) -> int | None:
    lo, hi = value_range

    match pred:
        case PredicateEven():
            first = lo if lo % 2 == 1 else lo + 1
            if first > hi:
                return None
            slots = ((hi - first) // 2) + 1
            return first + 2 * rng.randrange(slots)
        case PredicateOdd():
            first = lo if lo % 2 == 0 else lo + 1
            if first > hi:
                return None
            slots = ((hi - first) // 2) + 1
            return first + 2 * rng.randrange(slots)
        case PredicateLt(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if v_cmp <= hi:
                return rng.randint(max(v_cmp, lo), hi)
            return None
        case PredicateLe(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if v_cmp + 1 <= hi:
                return rng.randint(max(v_cmp + 1, lo), hi)
            return None
        case PredicateGt(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if lo <= v_cmp:
                return rng.randint(lo, min(v_cmp, hi))
            return None
        case PredicateGe(value=v):
            v_cmp = wrap_i32(v) if int32_wrap else v
            if lo <= v_cmp - 1:
                return rng.randint(lo, min(v_cmp - 1, hi))
            return None
        case PredicateModEq():
            def _matches(value: int) -> bool:
                return eval_predicate(
                    pred,
                    value,
                    int32_wrap=int32_wrap,
                )

            candidate = rng.randint(lo, hi)
            if not _matches(candidate):
                return candidate
            if lo == hi:
                return None
            if candidate < hi and not _matches(candidate + 1):
                return candidate + 1
            if candidate > lo and not _matches(candidate - 1):
                return candidate - 1
            for value in range(lo, hi + 1):
                if not _matches(value):
                    return value
            return None
        case PredicateNot() | PredicateAnd() | PredicateOr():
            return find_satisfying(
                lambda: rng.randint(lo, hi),
                lambda v: not eval_predicate(
                    pred,
                    v,
                    int32_wrap=int32_wrap,
                ),
            )
        case _:
            return rng.randint(lo, hi)


def _generate_random_list(
    length: int, value_range: tuple[int, int], rng: random.Random
) -> list[int]:
    return [rng.randint(*value_range) for _ in range(length)]


def _fit_to_length_bounds(
    values: list[int], length_bounds: tuple[int, int]
) -> list[int] | None:
    """Resize a query template so it stays within configured length bounds."""
    len_lo, len_hi = length_bounds
    if len_hi < len_lo:
        return None

    target_len = min(max(len(values), len_lo), len_hi)
    if target_len <= 0:
        return []
    if len(values) >= target_len:
        return values[:target_len]
    repeats = (target_len + len(values) - 1) // len(values)
    return (values * repeats)[:target_len]


def _generate_coverage_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random,
    *,
    int32_wrap: bool,
) -> list[Query]:
    """Empty list, single element, typical list."""
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    typical_len = (len_lo + len_hi) // 2

    queries: list[Query] = []
    queries.append(
        Query(
            input=[],
            output=eval_stateful(spec, [], int32_wrap=int32_wrap),
            tag=QueryTag.COVERAGE,
        )
    )
    single = [rng.randint(lo, hi)]
    queries.append(
        Query(
            input=single,
            output=eval_stateful(spec, single, int32_wrap=int32_wrap),
            tag=QueryTag.COVERAGE,
        )
    )
    typical_list = _generate_random_list(typical_len, (lo, hi), rng)
    queries.append(
        Query(
            input=typical_list,
            output=eval_stateful(spec, typical_list, int32_wrap=int32_wrap),
            tag=QueryTag.COVERAGE,
        )
    )
    return queries


def _generate_boundary_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random,
    *,
    int32_wrap: bool,
) -> list[Query]:
    """Predicate transitions: True->False, False->True, alternating."""
    lo, hi = axes.value_range
    pred = _get_predicate_info(spec)

    match_val = _make_matching_value(
        pred,
        (lo, hi),
        rng,
        int32_wrap=int32_wrap,
    )
    non_match_val = _make_non_matching_value(
        pred,
        (lo, hi),
        rng,
        int32_wrap=int32_wrap,
    )

    queries: list[Query] = []
    # Skip boundary queries if we couldn't find valid match/non-match values
    if match_val is None or non_match_val is None:
        return queries

    length_bounds = axes.list_length_range
    for template in (
        [match_val, match_val, non_match_val, non_match_val],
        [non_match_val, non_match_val, match_val, match_val],
        [match_val, non_match_val, match_val, non_match_val, match_val],
    ):
        fitted = _fit_to_length_bounds(template, length_bounds)
        if fitted is None:
            continue
        queries.append(
            Query(
                input=fitted,
                output=eval_stateful(spec, fitted, int32_wrap=int32_wrap),
                tag=QueryTag.BOUNDARY,
            )
        )
    return queries


def _generate_typical_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random,
    *,
    int32_wrap: bool,
) -> list[Query]:
    """Random lists of varying lengths."""
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range

    queries: list[Query] = []
    for _ in range(4):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        queries.append(
            Query(
                input=xs,
                output=eval_stateful(spec, xs, int32_wrap=int32_wrap),
                tag=QueryTag.TYPICAL,
            )
        )
    return queries


def _generate_adversarial_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random,
    *,
    int32_wrap: bool,
) -> list[Query]:
    """All-matching, all-non-matching, and extreme values."""
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    typical_len = (len_lo + len_hi) // 2
    pred = _get_predicate_info(spec)

    queries: list[Query] = []
    # All matching (skip individual None values)
    match_vals = [
        _make_matching_value(
            pred,
            (lo, hi),
            rng,
            int32_wrap=int32_wrap,
        )
        for _ in range(typical_len)
    ]
    all_match = [v for v in match_vals if v is not None]
    fitted_all_match = (
        _fit_to_length_bounds(all_match, axes.list_length_range)
        if all_match
        else None
    )
    if fitted_all_match is not None and all(
        eval_predicate(pred, x, int32_wrap=int32_wrap)
        for x in fitted_all_match
    ):
        queries.append(
            Query(
                input=fitted_all_match,
                output=eval_stateful(
                    spec,
                    fitted_all_match,
                    int32_wrap=int32_wrap,
                ),
                tag=QueryTag.ADVERSARIAL,
            )
        )
    # All non-matching (skip individual None values)
    non_match_vals = [
        _make_non_matching_value(
            pred,
            (lo, hi),
            rng,
            int32_wrap=int32_wrap,
        )
        for _ in range(typical_len)
    ]
    all_non_match = [v for v in non_match_vals if v is not None]
    fitted_all_non_match = (
        _fit_to_length_bounds(all_non_match, axes.list_length_range)
        if all_non_match
        else None
    )
    if fitted_all_non_match is not None and all(
        not eval_predicate(pred, x, int32_wrap=int32_wrap)
        for x in fitted_all_non_match
    ):
        queries.append(
            Query(
                input=fitted_all_non_match,
                output=eval_stateful(
                    spec,
                    fitted_all_non_match,
                    int32_wrap=int32_wrap,
                ),
                tag=QueryTag.ADVERSARIAL,
            )
        )
    # Extremes
    extremes = [lo, hi, 0, -1, 1, lo, hi]
    extremes = [x for x in extremes if lo <= x <= hi]
    fitted_extremes = _fit_to_length_bounds(extremes, axes.list_length_range)
    if fitted_extremes is not None:
        queries.append(
            Query(
                input=fitted_extremes,
                output=eval_stateful(
                    spec,
                    fitted_extremes,
                    int32_wrap=int32_wrap,
                ),
                tag=QueryTag.ADVERSARIAL,
            )
        )
    return queries


def generate_stateful_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random | None = None,
    *,
    int32_wrap: bool = True,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    queries = [
        *_generate_coverage_queries(
            spec,
            axes,
            rng,
            int32_wrap=int32_wrap,
        ),
        *_generate_boundary_queries(
            spec,
            axes,
            rng,
            int32_wrap=int32_wrap,
        ),
        *_generate_typical_queries(
            spec,
            axes,
            rng,
            int32_wrap=int32_wrap,
        ),
        *_generate_adversarial_queries(
            spec,
            axes,
            rng,
            int32_wrap=int32_wrap,
        ),
    ]
    return dedupe_queries(queries)
