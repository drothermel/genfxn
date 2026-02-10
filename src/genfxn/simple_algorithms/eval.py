from collections import Counter

from genfxn.core.int32 import i32_add, i32_sub, wrap_i32
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
    xs: list[int], spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec
) -> list[int]:
    ys = [wrap_i32(x) for x in xs]
    if spec.pre_filter is not None:
        ys = [x for x in ys if eval_predicate(spec.pre_filter, x)]
    if spec.pre_transform is not None:
        ys = [
            eval_transform(spec.pre_transform, x, int32_wrap=True)
            for x in ys
        ]
    return ys


def eval_most_frequent(spec: MostFrequentSpec, xs: list[int]) -> int:
    xs = _preprocess(xs, spec)
    if not xs:
        return wrap_i32(spec.empty_default)

    counts = Counter(xs)
    max_count = max(counts.values())
    candidates = [val for val, cnt in counts.items() if cnt == max_count]

    if len(candidates) > 1 and spec.tie_default is not None:
        return wrap_i32(spec.tie_default)

    if spec.tie_break == TieBreakMode.SMALLEST:
        return min(candidates)
    else:
        for x in xs:
            if x in candidates:
                return x
        return candidates[0]


def eval_count_pairs_sum(spec: CountPairsSumSpec, xs: list[int]) -> int:
    xs = _preprocess(xs, spec)
    target = wrap_i32(spec.target)
    if len(xs) < 2 and spec.short_list_default is not None:
        return wrap_i32(spec.short_list_default)

    if spec.counting_mode == CountingMode.ALL_INDICES:
        count = 0
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if i32_add(xs[i], xs[j]) == target:
                    count = i32_add(count, 1)
    else:
        seen_pairs: set[tuple[int, int]] = set()
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                if i32_add(xs[i], xs[j]) == target:
                    pair: tuple[int, int] = (
                        min(xs[i], xs[j]),
                        max(xs[i], xs[j]),
                    )
                    seen_pairs.add(pair)
        count = wrap_i32(len(seen_pairs))

    if count == 0 and spec.no_result_default is not None:
        return wrap_i32(spec.no_result_default)
    return wrap_i32(count)


def eval_max_window_sum(spec: MaxWindowSumSpec, xs: list[int]) -> int:
    xs = _preprocess(xs, spec)
    if not xs and spec.empty_default is not None:
        return wrap_i32(spec.empty_default)
    if len(xs) < spec.k:
        return wrap_i32(spec.invalid_k_default)

    window_sum = 0
    for x in xs[: spec.k]:
        window_sum = i32_add(window_sum, x)
    max_sum = window_sum

    for i in range(spec.k, len(xs)):
        window_sum = i32_add(i32_sub(window_sum, xs[i - spec.k]), xs[i])
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
