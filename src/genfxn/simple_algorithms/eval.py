from collections import Counter

from genfxn.core.predicates import eval_predicate
from genfxn.core.transforms import eval_transform
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)


def _preprocess(
    xs: list[int],
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec,
) -> list[int]:
    ys = list(xs)
    if spec.pre_filter is not None:
        ys = [x for x in ys if eval_predicate(spec.pre_filter, x)]
    if spec.pre_transform is not None:
        ys = [eval_transform(spec.pre_transform, x) for x in ys]
    return ys


def eval_most_frequent(
    spec: MostFrequentSpec,
    xs: list[int],
) -> int:
    xs = _preprocess(xs, spec)
    if not xs:
        return spec.empty_default

    counts = Counter(xs)
    max_count = max(counts.values())
    candidates = [val for val, cnt in counts.items() if cnt == max_count]

    if len(candidates) > 1 and spec.tie_default is not None:
        return spec.tie_default

    if spec.tie_break == TieBreakMode.SMALLEST:
        return min(candidates)

    for x in xs:
        if x in candidates:
            return x
    raise AssertionError("unreachable: xs non-empty and candidates derived from xs")


def eval_count_pairs_sum(
    spec: CountPairsSumSpec,
    xs: list[int],
) -> int:
    xs = _preprocess(xs, spec)
    target = spec.target
    if len(xs) < 2 and spec.short_list_default is not None:
        return spec.short_list_default

    if spec.counting_mode == CountingMode.ALL_INDICES:
        count = 0
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if xs[i] + xs[j] == target:
                    count += 1
    else:
        seen_pairs: set[tuple[int, int]] = set()
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if xs[i] + xs[j] == target:
                    pair: tuple[int, int] = (
                        min(xs[i], xs[j]),
                        max(xs[i], xs[j]),
                    )
                    seen_pairs.add(pair)
        count = len(seen_pairs)

    if count == 0 and spec.no_result_default is not None:
        return spec.no_result_default
    return count


def eval_max_window_sum(
    spec: MaxWindowSumSpec,
    xs: list[int],
) -> int:
    xs = _preprocess(xs, spec)
    if not xs and spec.empty_default is not None:
        return spec.empty_default
    if len(xs) < spec.k:
        return spec.invalid_k_default

    window_sum = 0
    for x in xs[: spec.k]:
        window_sum += x
    max_sum = window_sum

    for i in range(spec.k, len(xs)):
        window_sum = window_sum - xs[i - spec.k] + xs[i]
        max_sum = max(max_sum, window_sum)

    return max_sum


def eval_simple_algorithms(
    spec: SimpleAlgorithmsSpec,
    xs: list[int],
) -> int:
    match spec:
        case MostFrequentSpec():
            return eval_most_frequent(spec, xs)
        case CountPairsSumSpec():
            return eval_count_pairs_sum(spec, xs)
        case MaxWindowSumSpec():
            return eval_max_window_sum(spec, xs)
        case _:
            raise ValueError(f"Unknown simple algorithms spec: {spec}")
