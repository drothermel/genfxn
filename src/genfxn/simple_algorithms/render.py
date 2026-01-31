from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)


def render_most_frequent(
    spec: MostFrequentSpec, func_name: str = "f", var: str = "xs"
) -> str:
    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            f"    if not {var}:",
            f"        return {spec.empty_default}",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            "    candidates = [val for val, cnt in counts.items() if cnt == max_count]",  # noqa: E501
            "    return min(candidates)",
        ]
    else:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            f"    if not {var}:",
            f"        return {spec.empty_default}",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            "    candidates = set(val for val, cnt in counts.items() if cnt == max_count)",  # noqa: E501
            f"    for x in {var}:",
            "        if x in candidates:",
            "            return x",
            f"    return {spec.empty_default}",
        ]
    return "\n".join(lines)


def render_count_pairs_sum(
    spec: CountPairsSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            "    count = 0",
            f"    for i in range(len({var})):",
            f"        for j in range(i + 1, len({var})):",
            f"            if {var}[i] + {var}[j] == {spec.target}:",
            "                count += 1",
            "    return count",
        ]
    else:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            "    seen_pairs = set()",
            f"    for i in range(len({var})):",
            f"        for j in range(i + 1, len({var})):",
            f"            if {var}[i] + {var}[j] == {spec.target}:",
            f"                pair = tuple(sorted([{var}[i], {var}[j]]))",  # noqa: E501
            "                seen_pairs.add(pair)",
            "    return len(seen_pairs)",
        ]
    return "\n".join(lines)


def render_max_window_sum(
    spec: MaxWindowSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    lines = [
        f"def {func_name}({var}: list[int]) -> int:",
        f"    if len({var}) < {spec.k}:",
        f"        return {spec.invalid_k_default}",
        f"    window_sum = sum({var}[:{spec.k}])",
        "    max_sum = window_sum",
        f"    for i in range({spec.k}, len({var})):",
        f"        window_sum = window_sum - {var}[i - {spec.k}] + {var}[i]",
        "        max_sum = max(max_sum, window_sum)",
        "    return max_sum",
    ]
    return "\n".join(lines)


def render_simple_algorithms(
    spec: SimpleAlgorithmsSpec, func_name: str = "f", var: str = "xs"
) -> str:
    match spec:
        case MostFrequentSpec():
            return render_most_frequent(spec, func_name, var)
        case CountPairsSumSpec():
            return render_count_pairs_sum(spec, func_name, var)
        case MaxWindowSumSpec():
            return render_max_window_sum(spec, func_name, var)
        case _:
            raise ValueError(f"Unknown simple algorithms spec: {spec}")
