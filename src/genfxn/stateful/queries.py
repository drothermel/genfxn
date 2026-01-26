import random

from genfxn.core.models import Query, QueryTag
from genfxn.core.predicates import (
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
    eval_predicate,
)
from genfxn.stateful.eval import eval_stateful
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    StatefulAxes,
)


def _get_predicate_info(spec: StatefulSpec) -> tuple:
    match spec:
        case ConditionalLinearSumSpec(predicate=p):
            return p
        case ResettingBestPrefixSumSpec(reset_predicate=p):
            return p
        case LongestRunSpec(match_predicate=p):
            return p


def _make_matching_value(pred, value_range: tuple[int, int], rng: random.Random) -> int:
    lo, hi = value_range
    match pred:
        case PredicateEven():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 0]
            return rng.choice(candidates) if candidates else lo
        case PredicateOdd():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 1]
            return rng.choice(candidates) if candidates else lo + 1
        case PredicateLt(value=v):
            return rng.randint(lo, min(v - 1, hi)) if lo <= v - 1 else lo
        case PredicateLe(value=v):
            return rng.randint(lo, min(v, hi)) if lo <= v else lo
        case PredicateGt(value=v):
            return rng.randint(max(v + 1, lo), hi) if v + 1 <= hi else hi
        case PredicateGe(value=v):
            return rng.randint(max(v, lo), hi) if v <= hi else hi
        case PredicateModEq(divisor=d, remainder=r):
            candidates = [x for x in range(lo, hi + 1) if x % d == r]
            return rng.choice(candidates) if candidates else r
        case _:
            return rng.randint(lo, hi)


def _make_non_matching_value(
    pred, value_range: tuple[int, int], rng: random.Random
) -> int:
    lo, hi = value_range
    match pred:
        case PredicateEven():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 1]
            return rng.choice(candidates) if candidates else lo + 1
        case PredicateOdd():
            candidates = [x for x in range(lo, hi + 1) if x % 2 == 0]
            return rng.choice(candidates) if candidates else lo
        case PredicateLt(value=v):
            return rng.randint(max(v, lo), hi) if v <= hi else hi
        case PredicateLe(value=v):
            return rng.randint(max(v + 1, lo), hi) if v + 1 <= hi else hi
        case PredicateGt(value=v):
            return rng.randint(lo, min(v, hi)) if lo <= v else lo
        case PredicateGe(value=v):
            return rng.randint(lo, min(v - 1, hi)) if lo <= v - 1 else lo
        case PredicateModEq(divisor=d, remainder=r):
            candidates = [x for x in range(lo, hi + 1) if x % d != r]
            return rng.choice(candidates) if candidates else (r + 1) % d
        case _:
            return rng.randint(lo, hi)


def _generate_random_list(
    length: int, value_range: tuple[int, int], rng: random.Random
) -> list[int]:
    return [rng.randint(*value_range) for _ in range(length)]


def generate_stateful_queries(
    spec: StatefulSpec,
    axes: StatefulAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    queries: list[Query] = []
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    pred = _get_predicate_info(spec)

    # Coverage: empty list, single element, typical list
    queries.append(
        Query(input=[], output=eval_stateful(spec, []), tag=QueryTag.COVERAGE)
    )
    single = [rng.randint(lo, hi)]
    queries.append(
        Query(input=single, output=eval_stateful(spec, single), tag=QueryTag.COVERAGE)
    )
    typical_len = (len_lo + len_hi) // 2
    typical_list = _generate_random_list(typical_len, (lo, hi), rng)
    queries.append(
        Query(
            input=typical_list,
            output=eval_stateful(spec, typical_list),
            tag=QueryTag.COVERAGE,
        )
    )

    # Boundary: predicate transitions (True->False, False->True)
    # List with matching then non-matching
    match_val = _make_matching_value(pred, (lo, hi), rng)
    non_match_val = _make_non_matching_value(pred, (lo, hi), rng)
    transition_tf = [match_val, match_val, non_match_val, non_match_val]
    queries.append(
        Query(
            input=transition_tf,
            output=eval_stateful(spec, transition_tf),
            tag=QueryTag.BOUNDARY,
        )
    )
    # List with non-matching then matching
    transition_ft = [non_match_val, non_match_val, match_val, match_val]
    queries.append(
        Query(
            input=transition_ft,
            output=eval_stateful(spec, transition_ft),
            tag=QueryTag.BOUNDARY,
        )
    )
    # Alternating
    alternating = [match_val, non_match_val, match_val, non_match_val, match_val]
    queries.append(
        Query(
            input=alternating,
            output=eval_stateful(spec, alternating),
            tag=QueryTag.BOUNDARY,
        )
    )

    # Typical: random lists of varying lengths
    for _ in range(4):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        queries.append(
            Query(input=xs, output=eval_stateful(spec, xs), tag=QueryTag.TYPICAL)
        )

    # Adversarial: all-true, all-false, extremes
    # All matching
    all_match = [
        _make_matching_value(pred, (lo, hi), rng) for _ in range(typical_len)
    ]
    queries.append(
        Query(
            input=all_match,
            output=eval_stateful(spec, all_match),
            tag=QueryTag.ADVERSARIAL,
        )
    )
    # All non-matching
    all_non_match = [
        _make_non_matching_value(pred, (lo, hi), rng) for _ in range(typical_len)
    ]
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
    queries.append(
        Query(
            input=extremes, output=eval_stateful(spec, extremes), tag=QueryTag.ADVERSARIAL
        )
    )

    return _dedupe_queries(queries)


def _dedupe_queries(queries: list[Query]) -> list[Query]:
    seen: set[tuple[int, ...]] = set()
    result: list[Query] = []
    for q in queries:
        key = tuple(q.input)
        if key not in seen:
            seen.add(key)
            result.append(q)
    return result
