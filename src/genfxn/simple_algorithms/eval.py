from collections import Counter

from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)


def eval_most_frequent(spec: MostFrequentSpec, xs: list[int]) -> int:
    if not xs:
        return spec.empty_default

    counts = Counter(xs)
    max_count = max(counts.values())
    candidates = [val for val, cnt in counts.items() if cnt == max_count]

    if spec.tie_break == TieBreakMode.SMALLEST:
        return min(candidates)
    else:
        for x in xs:
            if x in candidates:
                return x
        return candidates[0]


def eval_count_pairs_sum(spec: CountPairsSumSpec, xs: list[int]) -> int:
    if spec.counting_mode == CountingMode.ALL_INDICES:
        count = 0
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if xs[i] + xs[j] == spec.target:
                    count += 1
        return count
    else:
        seen_pairs: set[tuple[int, int]] = set()
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if xs[i] + xs[j] == spec.target:
                    pair = tuple(sorted([xs[i], xs[j]]))
                    seen_pairs.add(pair)
        return len(seen_pairs)


def eval_max_window_sum(spec: MaxWindowSumSpec, xs: list[int]) -> int:
    if len(xs) < spec.k:
        return spec.invalid_k_default

    window_sum = sum(xs[: spec.k])
    max_sum = window_sum

    for i in range(spec.k, len(xs)):
        window_sum = window_sum - xs[i - spec.k] + xs[i]
        max_sum = max(max_sum, window_sum)

    return max_sum


def eval_simple_algorithms(spec: SimpleAlgorithmsSpec, xs: list[int]) -> int:
    match spec:
        case MostFrequentSpec():
            return eval_most_frequent(spec, xs)
        case CountPairsSumSpec():
            return eval_count_pairs_sum(spec, xs)
        case MaxWindowSumSpec():
            return eval_max_window_sum(spec, xs)
        case _:
            raise ValueError(f"Unknown simple algorithms spec: {spec}")
