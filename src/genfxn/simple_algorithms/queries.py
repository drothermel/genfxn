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
    length: int, value_range: tuple[int, int], rng: random.Random
) -> list[int]:
    return [rng.randint(*value_range) for _ in range(length)]


def _mid(lo: int, hi: int) -> int:
    return (lo + hi) // 2


def _clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def _distinct_in_range(lo: int, hi: int, n: int) -> list[int]:
    """Up to n distinct integers in [lo, hi]; fewer if range is too narrow."""
    span = hi - lo + 1
    if span <= 0:
        return [lo] * min(1, n)
    return list(range(lo, min(lo + n, hi + 1)))


def _preprocess_count_pairs_input(
    spec: CountPairsSumSpec, xs: list[int]
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
    spec: CountPairsSumSpec, axes: SimpleAlgorithmsAxes, rng: random.Random
) -> list[int] | None:
    lo, hi = axes.value_range
    len_lo, len_hi = axes.list_length_range
    if len_hi < len_lo:
        return None

    # Try random candidates first.
    max_len = min(len_hi, 5)
    if max_len >= len_lo:
        for _ in range(80):
            length = rng.randint(len_lo, max_len)
            candidate = _generate_random_list(length, (lo, hi), rng)
            processed = _preprocess_count_pairs_input(spec, candidate)
            if not _has_pair_sum(processed, spec.target):
                return candidate

    # Deterministic fallback from non-complement values in range.
    target = spec.target
    raw: list[int] = []
    for value in range(lo, hi + 1):
        if (target - value) in raw:
            continue
        raw.append(value)
        if len(raw) >= max(1, len_lo):
            candidate = raw[: min(len(raw), max(1, len_hi))]
            processed = _preprocess_count_pairs_input(spec, candidate)
            if not _has_pair_sum(processed, target):
                return candidate
        if len(raw) >= max(1, min(len_hi, 5)):
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
    if len(values) >= target_len:
        return values[:target_len]
    repeats = (target_len + len(values) - 1) // len(values)
    return (values * repeats)[:target_len]


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

    # Clear winner - no tie (one value appears 3x, others once; all in [lo, hi])
    three_vals = _distinct_in_range(lo, hi, 3)
    if len(three_vals) >= 3:
        a, b, c = three_vals[0], three_vals[1], three_vals[2]
        clear_winner = [a, a, a, b, c]
        queries.append(
            Query(
                input=clear_winner,
                output=eval_simple_algorithms(spec, clear_winner),
                tag=QueryTag.TYPICAL,
            )
        )

    # Tie between values - tests tie_break semantics
    # [b,a,b,a] vs [a,b,a,b] - first_seen differs; need 2 distinct in [lo, hi]
    two_vals = _distinct_in_range(lo, hi, 2)
    if len(two_vals) >= 2:
        a, b = two_vals[0], two_vals[1]
        tie_a = [b, a, b, a]
        tie_b = [a, b, a, b]
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

    # Multi-way tie (3 distinct values, each 2x)
    three_for_tie = _distinct_in_range(lo, hi, 3)
    if len(three_for_tie) >= 3:
        a, b, c = three_for_tie[0], three_for_tie[1], three_for_tie[2]
        multi_tie = [a, b, c, a, b, c]
        queries.append(
            Query(
                input=multi_tie,
                output=eval_simple_algorithms(spec, multi_tie),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    # All same value (within [lo, hi])
    mid = _mid(lo, hi)
    all_same = [mid, mid, mid, mid]
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

    # Single element - no pairs (value in [lo, hi])
    single_val = _clamp(target // 2, lo, hi)
    queries.append(
        Query(
            input=[single_val],
            output=eval_simple_algorithms(spec, [single_val]),
            tag=QueryTag.COVERAGE,
        )
    )

    # Two elements that sum to target (both in [lo, hi])
    pair_lo = max(lo, target - hi)
    pair_hi = min(hi, target - lo)
    if pair_lo <= pair_hi:
        half = (pair_lo + pair_hi) // 2
        other_half = target - half
        pair_list = [half, other_half]
        queries.append(
            Query(
                input=pair_list,
                output=eval_simple_algorithms(spec, pair_list),
                tag=QueryTag.BOUNDARY,
            )
        )

    # Two elements that don't sum to target (both in [lo, hi])
    two_distinct = _distinct_in_range(lo, hi, 3)
    if len(two_distinct) >= 2:
        na, nb = two_distinct[0], two_distinct[1]
        if na + nb == target and len(two_distinct) >= 3:
            nb = two_distinct[2]
        if na + nb != target:
            no_pair = [na, nb]
            queries.append(
                Query(
                    input=no_pair,
                    output=eval_simple_algorithms(spec, no_pair),
                    tag=QueryTag.BOUNDARY,
                )
            )

    # Duplicates - distinguishes ALL_INDICES from UNIQUE_VALUES
    # [v, v, target-v] -> ALL_INDICES=2 pairs, UNIQUE_VALUES=1
    dup_v_lo = max(lo, target - hi)
    dup_v_hi = min(hi, target - lo)
    if dup_v_lo <= dup_v_hi:
        v = (dup_v_lo + dup_v_hi) // 2
        dups = [v, v, target - v]
        queries.append(
            Query(
                input=dups,
                output=eval_simple_algorithms(spec, dups),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    # More duplicates: [a, a, b, b] where a+b=target (a, b in [lo, hi])
    if pair_lo <= pair_hi:
        a = (pair_lo + pair_hi) // 2
        b = target - a
        more_dups = [a, a, b, b]
        queries.append(
            Query(
                input=more_dups,
                output=eval_simple_algorithms(spec, more_dups),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    # Self-pairing: target=2v -> [v,v,v] (only when target//2 in [lo, hi])
    if target % 2 == 0:
        self_val = target // 2
        if lo <= self_val <= hi:
            self_pairs = [self_val, self_val, self_val]
            queries.append(
                Query(
                    input=self_pairs,
                    output=eval_simple_algorithms(spec, self_pairs),
                    tag=QueryTag.ADVERSARIAL,
                )
            )

    # No pairs: explicitly enforce zero valid pair sums after preprocessing.
    no_pairs = _find_no_pairs_input(spec, axes, rng)
    if no_pairs is not None:
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
    length_bounds = axes.list_length_range

    # Empty list - k > len
    queries.append(
        Query(
            input=[],
            output=eval_simple_algorithms(spec, []),
            tag=QueryTag.COVERAGE,
        )
    )

    # List shorter than k (values in [lo, hi]; length exactly k-1)
    if k - 1 > 0:
        short_base = _distinct_in_range(lo, hi, k - 1)
        # Repeat base values to fill length k-1, then truncate.
        short = (short_base * ((k - 1) // max(1, len(short_base)) + 1))[: k - 1]
        if len(short) == k - 1:
            queries.append(
                Query(
                    input=short,
                    output=spec.invalid_k_default,
                    tag=QueryTag.BOUNDARY,
                )
            )

    # Exactly k elements (distinct in [lo, hi])
    exact_k = _distinct_in_range(lo, hi, k)
    if len(exact_k) >= k:
        exact_k = exact_k[:k]
        queries.append(
            Query(
                input=exact_k,
                output=eval_simple_algorithms(spec, exact_k),
                tag=QueryTag.BOUNDARY,
            )
        )

    # k=1 edge case test (several values in [lo, hi], max is one of them)
    if k == 1 and hi >= lo:
        single_vals = _distinct_in_range(lo, hi, 8)
        if len(single_vals) >= 8:
            single_max_template = [
                single_vals[2],
                single_vals[0],
                single_vals[3],
                single_vals[0],
                single_vals[4],
                single_vals[7],
                single_vals[1],
                single_vals[5],
            ]
            single_max = _fit_length_bounds(
                single_max_template, length_bounds, min_len=k
            )
            if single_max is not None:
                queries.append(
                    Query(
                        input=single_max,
                        output=eval_simple_algorithms(spec, single_max),
                        tag=QueryTag.BOUNDARY,
                    )
                )

    # All at low end of range (adversarial: small window sums)
    low_vals = _fit_length_bounds([lo] * 8, length_bounds, min_len=k)
    if low_vals is not None and len(low_vals) >= k:
        queries.append(
            Query(
                input=low_vals,
                output=eval_simple_algorithms(spec, low_vals),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    # Max at start (hi repeated then lo repeated; all in [lo, hi])
    max_at_start = _fit_length_bounds(
        [hi, hi, hi] + [lo] * 5, length_bounds, min_len=k
    )
    if max_at_start is not None and len(max_at_start) >= k:
        queries.append(
            Query(
                input=max_at_start,
                output=eval_simple_algorithms(spec, max_at_start),
                tag=QueryTag.TYPICAL,
            )
        )

    # Max at end (lo repeated then hi repeated)
    max_at_end = _fit_length_bounds(
        [lo] * 5 + [hi, hi, hi], length_bounds, min_len=k
    )
    if max_at_end is not None and len(max_at_end) >= k:
        queries.append(
            Query(
                input=max_at_end,
                output=eval_simple_algorithms(spec, max_at_end),
                tag=QueryTag.TYPICAL,
            )
        )

    mid = _mid(lo, hi)
    # All same values (mid in [lo, hi])
    all_same = _fit_length_bounds([mid] * 10, length_bounds, min_len=k)
    if all_same is not None and len(all_same) >= k:
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
        length = rng.randint(max(k, len_lo), len_hi)
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

    return dedupe_queries(queries)
