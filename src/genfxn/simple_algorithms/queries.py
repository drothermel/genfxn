import random

from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.core.predicates import eval_predicate
from genfxn.core.transforms import eval_transform
from genfxn.simple_algorithms.eval import eval_simple_algorithms
from genfxn.simple_algorithms.models import (
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
)


def _generate_random_list(
    length: int,
    value_range: tuple[int, int],
    rng: random.Random,
) -> list[int]:
    return [rng.randint(*value_range) for _ in range(length)]


def _mid(lo: int, hi: int) -> int:
    return (lo + hi) // 2


def _clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _distinct_in_range(lo: int, hi: int, n: int) -> list[int]:
    span = hi - lo + 1
    if span <= 0:
        return [lo] * min(1, n)
    return list(range(lo, min(lo + n, hi + 1)))


def _append_query(
    queries: list[Query],
    spec: SimpleAlgorithmsSpec,
    xs: list[int],
    tag: QueryTag,
) -> None:
    queries.append(
        Query(
            input=xs,
            output=eval_simple_algorithms(spec, xs),
            tag=tag,
        )
    )


def _preprocess_count_pairs_input(
    spec: CountPairsSumSpec,
    xs: list[int],
) -> list[int]:
    ys = list(xs)
    if spec.pre_filter is not None:
        ys = [x for x in ys if eval_predicate(spec.pre_filter, x)]
    if spec.pre_transform is not None:
        ys = [eval_transform(spec.pre_transform, x) for x in ys]
    return ys


def _has_pair_sum(xs: list[int], target: int) -> bool:
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            if xs[i] + xs[j] == target:
                return True
    return False


def _find_no_pairs_input(
    spec: CountPairsSumSpec,
    axes: SimpleAlgorithmsAxes,
    rng: random.Random,
) -> list[int] | None:
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    if len_hi < len_lo:
        return None
    # "No pairs" requires at least 2 elements; axes must allow that.
    if len_hi < 2:
        return None

    max_len = min(len_hi, 5)
    effective_min_len = max(2, len_lo)
    if effective_min_len <= max_len:
        for _ in range(80):
            length = rng.randint(effective_min_len, max_len)
            candidate = _generate_random_list(length, (lo, hi), rng)
            processed = _preprocess_count_pairs_input(spec, candidate)
            if not _has_pair_sum(processed, spec.target):
                return candidate

    target = spec.target
    raw: list[int] = []
    for value in range(lo, hi + 1):
        if (target - value) in raw:
            continue
        raw.append(value)
        if len(raw) >= max(2, len_lo):
            candidate = raw[: min(len(raw), max(2, len_hi))]
            processed = _preprocess_count_pairs_input(spec, candidate)
            if not _has_pair_sum(processed, target):
                return candidate
        if len(raw) >= max(2, min(len_hi, 5)):
            break

    return None


def _fit_length_bounds(
    values: list[int],
    length_bounds: tuple[int, int],
    *,
    min_len: int = 0,
) -> list[int] | None:
    len_lo, len_hi = length_bounds
    lower = max(len_lo, min_len)
    if lower > len_hi:
        return None
    target_len = min(max(len(values), lower), len_hi)
    if target_len <= 0:
        return []
    if not values:
        return None
    if len(values) >= target_len:
        return values[:target_len]
    repeats = (target_len + len(values) - 1) // len(values)
    return (values * repeats)[:target_len]


def _generate_most_frequent_queries(
    spec: MostFrequentSpec,
    axes: SimpleAlgorithmsAxes,
    rng: random.Random,
) -> list[Query]:
    queries: list[Query] = []
    lo, hi = axes.value_range
    length_bounds = axes.list_length_range

    empty = _fit_length_bounds([], length_bounds, min_len=0)
    if empty is not None:
        _append_query(queries, spec, empty, QueryTag.COVERAGE)

    single = _fit_length_bounds([rng.randint(lo, hi)], length_bounds, min_len=1)
    if single is not None:
        _append_query(queries, spec, single, QueryTag.COVERAGE)

    unique_vals = _fit_length_bounds(
        list(range(lo, min(lo + 5, hi + 1))),
        length_bounds,
        min_len=1,
    )
    if unique_vals is not None:
        _append_query(queries, spec, unique_vals, QueryTag.BOUNDARY)

    three_vals = _distinct_in_range(lo, hi, 3)
    if len(three_vals) >= 3:
        a, b, c = three_vals[0], three_vals[1], three_vals[2]
        clear_winner = _fit_length_bounds(
            [a, a, a, b, c],
            length_bounds,
            min_len=1,
        )
        if clear_winner is not None:
            _append_query(queries, spec, clear_winner, QueryTag.TYPICAL)

    two_vals = _distinct_in_range(lo, hi, 2)
    if len(two_vals) >= 2:
        a, b = two_vals[0], two_vals[1]
        tie_a = _fit_length_bounds([b, a, b, a], length_bounds, min_len=2)
        tie_b = _fit_length_bounds([a, b, a, b], length_bounds, min_len=2)
        if tie_a is not None:
            _append_query(queries, spec, tie_a, QueryTag.BOUNDARY)
        if tie_b is not None:
            _append_query(queries, spec, tie_b, QueryTag.BOUNDARY)

    len_lo, len_hi = length_bounds
    for _ in range(2):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        _append_query(queries, spec, xs, QueryTag.TYPICAL)

    return queries


def _generate_count_pairs_queries(
    spec: CountPairsSumSpec,
    axes: SimpleAlgorithmsAxes,
    rng: random.Random,
) -> list[Query]:
    queries: list[Query] = []
    target = spec.target
    lo, hi = axes.value_range
    length_bounds = axes.list_length_range

    empty = _fit_length_bounds([], length_bounds, min_len=0)
    if empty is not None:
        _append_query(queries, spec, empty, QueryTag.COVERAGE)

    single_val = _clamp(target // 2, lo, hi)
    single = _fit_length_bounds([single_val], length_bounds, min_len=1)
    if single is not None:
        _append_query(queries, spec, single, QueryTag.COVERAGE)

    pair_lo = max(lo, target - hi)
    pair_hi = min(hi, target - lo)
    if pair_lo <= pair_hi:
        a = (pair_lo + pair_hi) // 2
        b = target - a
        pair_list = _fit_length_bounds([a, b], length_bounds, min_len=2)
        if pair_list is not None:
            _append_query(queries, spec, pair_list, QueryTag.BOUNDARY)

    no_pairs = _find_no_pairs_input(spec, axes, rng)
    if no_pairs is not None:
        _append_query(queries, spec, no_pairs, QueryTag.TYPICAL)

    len_lo, len_hi = axes.list_length_range
    for _ in range(2):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        _append_query(queries, spec, xs, QueryTag.TYPICAL)

    return queries


def _generate_max_window_queries(
    spec: MaxWindowSumSpec,
    axes: SimpleAlgorithmsAxes,
    rng: random.Random,
) -> list[Query]:
    queries: list[Query] = []
    k = spec.k
    lo, hi = axes.value_range
    length_bounds = axes.list_length_range

    empty = _fit_length_bounds([], length_bounds, min_len=0)
    if empty is not None and len(empty) < k:
        _append_query(queries, spec, empty, QueryTag.COVERAGE)

    if k - 1 > 0:
        short_base = _distinct_in_range(lo, hi, max(1, k - 1))
        repeats = ((k - 1) // max(1, len(short_base))) + 1
        short_template = (short_base * repeats)[: k - 1]
        short = _fit_length_bounds(short_template, length_bounds, min_len=0)
        if short is not None and len(short) == (k - 1):
            _append_query(queries, spec, short, QueryTag.BOUNDARY)

    exact_k = _distinct_in_range(lo, hi, max(1, k))
    if len(exact_k) >= k:
        exact_fit = _fit_length_bounds(
            exact_k[:k],
            length_bounds,
            min_len=k,
        )
        if exact_fit is not None and len(exact_fit) >= k:
            _append_query(queries, spec, exact_fit, QueryTag.BOUNDARY)

    min_len = min(k, max(1, length_bounds[0]))
    max_at_start = _fit_length_bounds(
        [hi, hi, hi] + [lo] * 5,
        length_bounds,
        min_len=min_len,
    )
    if max_at_start is not None:
        _append_query(queries, spec, max_at_start, QueryTag.TYPICAL)

    max_at_end = _fit_length_bounds(
        [lo] * 5 + [hi, hi, hi],
        length_bounds,
        min_len=min_len,
    )
    if max_at_end is not None:
        _append_query(queries, spec, max_at_end, QueryTag.TYPICAL)

    mid = _mid(lo, hi)
    all_same = _fit_length_bounds(
        [mid] * 10,
        length_bounds,
        min_len=min_len,
    )
    if all_same is not None:
        _append_query(queries, spec, all_same, QueryTag.TYPICAL)

    len_lo, len_hi = axes.list_length_range
    for _ in range(2):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        _append_query(queries, spec, xs, QueryTag.TYPICAL)

    return queries


def generate_simple_algorithms_queries(
    spec: SimpleAlgorithmsSpec,
    axes: SimpleAlgorithmsAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    match spec:
        case MostFrequentSpec():
            queries = _generate_most_frequent_queries(spec, axes, rng)
        case CountPairsSumSpec():
            queries = _generate_count_pairs_queries(spec, axes, rng)
        case MaxWindowSumSpec():
            queries = _generate_max_window_queries(spec, axes, rng)
        case _:
            raise ValueError(f"Unknown spec: {spec}")

    # Guardrail: keep at least 5 distinct inputs per task. seen_inputs drives
    # the loop; final dedupe_queries produces the unique list.
    seen_inputs = {tuple(q.input) for q in queries}
    attempts = 0
    while len(seen_inputs) < 5 and attempts < 200:
        attempts += 1
        length = rng.randint(*axes.list_length_range)
        candidate = _generate_random_list(length, axes.value_range, rng)
        key = tuple(candidate)
        if key in seen_inputs:
            continue
        seen_inputs.add(key)
        _append_query(queries, spec, candidate, QueryTag.TYPICAL)

    return dedupe_queries(queries)
