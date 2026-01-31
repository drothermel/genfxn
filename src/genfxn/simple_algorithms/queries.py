import random

from genfxn.core.models import Query, QueryTag
from genfxn.simple_algorithms.eval import eval_simple_algorithms
from genfxn.simple_algorithms.models import (
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
)


def _generate_random_list(
    length: int, value_range: tuple[int, int], rng: random.Random
) -> list[int]:
    return [rng.randint(*value_range) for _ in range(length)]


def _generate_most_frequent_queries(
    spec: MostFrequentSpec, axes: SimpleAlgorithmsAxes, rng: random.Random
) -> list[Query]:
    queries: list[Query] = []
    lo, hi = axes.value_range

    # Empty list - edge case
    queries.append(
        Query(input=[], output=spec.empty_default, tag=QueryTag.COVERAGE)
    )

    # Single element
    single = [rng.randint(lo, hi)]
    queries.append(
        Query(
            input=single,
            output=eval_simple_algorithms(spec, single),
            tag=QueryTag.COVERAGE,
        )
    )

    # All unique - tests tie break
    unique_vals = list(range(lo, min(lo + 5, hi + 1)))
    if unique_vals:
        queries.append(
            Query(
                input=unique_vals,
                output=eval_simple_algorithms(spec, unique_vals),
                tag=QueryTag.BOUNDARY,
            )
        )

    # Clear winner - no tie
    clear_winner = [1, 1, 1, 2, 3]
    queries.append(
        Query(
            input=clear_winner,
            output=eval_simple_algorithms(spec, clear_winner),
            tag=QueryTag.TYPICAL,
        )
    )

    # Tie between values - tests tie_break semantics
    # [2,1,2,1] vs [1,2,1,2] - first_seen differs
    tie_a = [2, 1, 2, 1]
    tie_b = [1, 2, 1, 2]
    queries.append(
        Query(
            input=tie_a,
            output=eval_simple_algorithms(spec, tie_a),
            tag=QueryTag.BOUNDARY,
        )
    )
    queries.append(
        Query(
            input=tie_b,
            output=eval_simple_algorithms(spec, tie_b),
            tag=QueryTag.BOUNDARY,
        )
    )

    # Multi-way tie
    multi_tie = [1, 2, 3, 1, 2, 3]
    queries.append(
        Query(
            input=multi_tie,
            output=eval_simple_algorithms(spec, multi_tie),
            tag=QueryTag.ADVERSARIAL,
        )
    )

    # All same value
    all_same = [5, 5, 5, 5]
    queries.append(
        Query(
            input=all_same,
            output=eval_simple_algorithms(spec, all_same),
            tag=QueryTag.TYPICAL,
        )
    )

    # Typical random
    len_lo, len_hi = axes.list_length_range
    for _ in range(2):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        queries.append(
            Query(
                input=xs,
                output=eval_simple_algorithms(spec, xs),
                tag=QueryTag.TYPICAL,
            )
        )

    return queries


def _generate_count_pairs_queries(
    spec: CountPairsSumSpec, axes: SimpleAlgorithmsAxes, rng: random.Random
) -> list[Query]:
    queries: list[Query] = []
    target = spec.target
    lo, hi = axes.value_range

    # Empty list
    queries.append(
        Query(
            input=[],
            output=eval_simple_algorithms(spec, []),
            tag=QueryTag.COVERAGE,
        )
    )

    # Single element - no pairs
    queries.append(
        Query(
            input=[target // 2],
            output=eval_simple_algorithms(spec, [target // 2]),
            tag=QueryTag.COVERAGE,
        )
    )

    # Two elements that sum to target
    half = target // 2
    other_half = target - half
    pair_list = [half, other_half]
    queries.append(
        Query(
            input=pair_list,
            output=eval_simple_algorithms(spec, pair_list),
            tag=QueryTag.BOUNDARY,
        )
    )

    # Two elements that don't sum to target
    no_pair = [half, half + 100]
    queries.append(
        Query(
            input=no_pair,
            output=eval_simple_algorithms(spec, no_pair),
            tag=QueryTag.BOUNDARY,
        )
    )

    # Duplicates - distinguishes ALL_INDICES from UNIQUE_VALUES
    # [v, v, target-v] -> ALL_INDICES=2 pairs, UNIQUE_VALUES=1 unique pair
    v = target // 3
    dups = [v, v, target - v]
    queries.append(
        Query(
            input=dups,
            output=eval_simple_algorithms(spec, dups),
            tag=QueryTag.ADVERSARIAL,
        )
    )

    # More duplicates
    # [a, a, b, b] where a+b=target -> ALL_INDICES=4, UNIQUE_VALUES=1
    a = target // 2
    b = target - a
    more_dups = [a, a, b, b]
    queries.append(
        Query(
            input=more_dups,
            output=eval_simple_algorithms(spec, more_dups),
            tag=QueryTag.ADVERSARIAL,
        )
    )

    # Self-pairing: target=2v -> [v,v,v] has multiple self-pairs
    if target % 2 == 0:
        self_val = target // 2
        self_pairs = [self_val, self_val, self_val]
        queries.append(
            Query(
                input=self_pairs,
                output=eval_simple_algorithms(spec, self_pairs),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    # No pairs: five distinct values all < target//2, or [v]*5 with 2*v != target
    start = max(lo, 0)
    candidates = [start + i for i in range(5) if start + i < target // 2]
    if len(candidates) >= 5:
        no_pairs = candidates[:5]
    else:
        v = start
        if 2 * v == target:
            v = start + 1
        no_pairs = [v] * 5
    queries.append(
        Query(
            input=no_pairs,
            output=eval_simple_algorithms(spec, no_pairs),
            tag=QueryTag.TYPICAL,
        )
    )

    # Random typical
    len_lo, len_hi = axes.list_length_range
    for _ in range(2):
        length = rng.randint(len_lo, len_hi)
        xs = _generate_random_list(length, (lo, hi), rng)
        queries.append(
            Query(
                input=xs,
                output=eval_simple_algorithms(spec, xs),
                tag=QueryTag.TYPICAL,
            )
        )

    return queries


def _generate_max_window_queries(
    spec: MaxWindowSumSpec, axes: SimpleAlgorithmsAxes, rng: random.Random
) -> list[Query]:
    queries: list[Query] = []
    k = spec.k
    lo, hi = axes.value_range

    # Empty list - k > len
    queries.append(
        Query(
            input=[],
            output=spec.invalid_k_default,
            tag=QueryTag.COVERAGE,
        )
    )

    # List shorter than k
    short = list(range(1, k))
    if short:
        queries.append(
            Query(
                input=short,
                output=spec.invalid_k_default,
                tag=QueryTag.BOUNDARY,
            )
        )

    # Exactly k elements
    exact_k = list(range(1, k + 1))
    queries.append(
        Query(
            input=exact_k,
            output=eval_simple_algorithms(spec, exact_k),
            tag=QueryTag.BOUNDARY,
        )
    )

    # k=1 edge case test
    if k == 1:
        single_max = [3, 1, 4, 1, 5, 9, 2, 6]
        queries.append(
            Query(
                input=single_max,
                output=eval_simple_algorithms(spec, single_max),
                tag=QueryTag.BOUNDARY,
            )
        )

    # All negative
    all_neg = [-5, -3, -7, -1, -4, -2, -8, -6]
    if len(all_neg) >= k:
        queries.append(
            Query(
                input=all_neg,
                output=eval_simple_algorithms(spec, all_neg),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    # Max at start
    max_at_start = [10, 10, 10] + [1] * 5
    if len(max_at_start) >= k:
        queries.append(
            Query(
                input=max_at_start,
                output=eval_simple_algorithms(spec, max_at_start),
                tag=QueryTag.TYPICAL,
            )
        )

    # Max at end
    max_at_end = [1] * 5 + [10, 10, 10]
    if len(max_at_end) >= k:
        queries.append(
            Query(
                input=max_at_end,
                output=eval_simple_algorithms(spec, max_at_end),
                tag=QueryTag.TYPICAL,
            )
        )

    # All same values
    all_same = [5] * 10
    if len(all_same) >= k:
        queries.append(
            Query(
                input=all_same,
                output=eval_simple_algorithms(spec, all_same),
                tag=QueryTag.TYPICAL,
            )
        )

    # Random typical
    len_lo, len_hi = axes.list_length_range
    for _ in range(2):
        length = max(k, rng.randint(len_lo, len_hi))
        xs = _generate_random_list(length, (lo, hi), rng)
        queries.append(
            Query(
                input=xs,
                output=eval_simple_algorithms(spec, xs),
                tag=QueryTag.TYPICAL,
            )
        )

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
