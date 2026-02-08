import random

from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.core.query_utils import find_satisfying
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
    pred, value_range: tuple[int, int], rng: random.Random
) -> int | None:
    lo, hi = value_range

    match pred:
        case PredicateEven():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 0]
            return rng.choice(candidates) if candidates else None
        case PredicateOdd():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 1]
            return rng.choice(candidates) if candidates else None
        case PredicateLt(value=v):
            if lo <= v - 1:
                return rng.randint(lo, min(v - 1, hi))
            return None
        case PredicateLe(value=v):
            if lo <= v:
                return rng.randint(lo, min(v, hi))
            return None
        case PredicateGt(value=v):
            if v + 1 <= hi:
                return rng.randint(max(v + 1, lo), hi)
            return None
        case PredicateGe(value=v):
            if v <= hi:
                return rng.randint(max(v, lo), hi)
            return None
        case PredicateModEq(divisor=d, remainder=r):
            candidates = [x for x in range(lo, hi + 1) if x % d == r]
            if candidates:
                return rng.choice(candidates)
            return None
        case PredicateNot() | PredicateAnd() | PredicateOr():
            return find_satisfying(
                lambda: rng.randint(lo, hi),
                lambda v: eval_predicate(pred, v),
            )
        case _:
            return rng.randint(lo, hi)


def _make_non_matching_value(
    pred, value_range: tuple[int, int], rng: random.Random
) -> int | None:
    lo, hi = value_range

    match pred:
        case PredicateEven():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 1]
            return rng.choice(candidates) if candidates else None
        case PredicateOdd():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 0]
            return rng.choice(candidates) if candidates else None
        case PredicateLt(value=v):
            if v <= hi:
                return rng.randint(max(v, lo), hi)
            return None
        case PredicateLe(value=v):
            if v + 1 <= hi:
                return rng.randint(max(v + 1, lo), hi)
            return None
        case PredicateGt(value=v):
            if lo <= v:
                return rng.randint(lo, min(v, hi))
            return None
        case PredicateGe(value=v):
            if lo <= v - 1:
                return rng.randint(lo, min(v - 1, hi))
            return None
        case PredicateModEq(divisor=d, remainder=r):
            candidates = [x for x in range(lo, hi + 1) if x % d != r]
            if candidates:
                return rng.choice(candidates)
            return None
        case PredicateNot() | PredicateAnd() | PredicateOr():
            return find_satisfying(
                lambda: rng.randint(lo, hi),
                lambda v: not eval_predicate(pred, v),
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
    spec: StatefulSpec, axes: StatefulAxes, rng: random.Random
) -> list[Query]:
    """Empty list, single element, typical list."""
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    typical_len = (len_lo + len_hi) // 2

    queries: list[Query] = []
    queries.append(
        Query(input=[], output=eval_stateful(spec, []), tag=QueryTag.COVERAGE)
    )
    single = [rng.randint(lo, hi)]
    queries.append(
        Query(
            input=single,
            output=eval_stateful(spec, single),
            tag=QueryTag.COVERAGE,
        )
    )
    typical_list = _generate_random_list(typical_len, (lo, hi), rng)
    queries.append(
        Query(
            input=typical_list,
            output=eval_stateful(spec, typical_list),
            tag=QueryTag.COVERAGE,
        )
    )
    return queries


def _generate_boundary_queries(
    spec: StatefulSpec, axes: StatefulAxes, rng: random.Random
) -> list[Query]:
    """Predicate transitions: True->False, False->True, alternating."""
    lo, hi = axes.value_range
    pred = _get_predicate_info(spec)

    match_val = _make_matching_value(pred, (lo, hi), rng)
    non_match_val = _make_non_matching_value(pred, (lo, hi), rng)

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
                output=eval_stateful(spec, fitted),
                tag=QueryTag.BOUNDARY,
            )
        )
    return queries


def _generate_typical_queries(
    spec: StatefulSpec, axes: StatefulAxes, rng: random.Random
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
                input=xs, output=eval_stateful(spec, xs), tag=QueryTag.TYPICAL
            )
        )
    return queries


def _generate_adversarial_queries(
    spec: StatefulSpec, axes: StatefulAxes, rng: random.Random
) -> list[Query]:
    """All-matching, all-non-matching, and extreme values."""
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    typical_len = (len_lo + len_hi) // 2
    pred = _get_predicate_info(spec)

    queries: list[Query] = []
    # All matching (skip individual None values)
    match_vals = [
        _make_matching_value(pred, (lo, hi), rng) for _ in range(typical_len)
    ]
    all_match = [v for v in match_vals if v is not None]
    if all_match:
        queries.append(
            Query(
                input=all_match,
                output=eval_stateful(spec, all_match),
                tag=QueryTag.ADVERSARIAL,
            )
        )
    # All non-matching (skip individual None values)
    non_match_vals = [
        _make_non_matching_value(pred, (lo, hi), rng)
        for _ in range(typical_len)
    ]
    all_non_match = [v for v in non_match_vals if v is not None]
    if all_non_match:
        queries.append(
            Query(
                input=all_non_match,
                output=eval_stateful(spec, all_non_match),
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
                output=eval_stateful(spec, fitted_extremes),
                tag=QueryTag.ADVERSARIAL,
            )
        )
    return queries


def generate_stateful_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    queries = [
        *_generate_coverage_queries(spec, axes, rng),
        *_generate_boundary_queries(spec, axes, rng),
        *_generate_typical_queries(spec, axes, rng),
        *_generate_adversarial_queries(spec, axes, rng),
    ]
    return dedupe_queries(queries)
