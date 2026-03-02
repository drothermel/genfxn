from genfxn.core.predicates import render_predicate
from genfxn.core.transforms import render_transform
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)


def _render_preprocess(
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec,
    var: str,
) -> list[str]:
    lines: list[str] = []
    if spec.pre_filter is not None:
        cond = render_predicate(spec.pre_filter, "x")
        lines.append(f"    {var} = [x for x in {var} if {cond}]")
    if spec.pre_transform is not None:
        expr = render_transform(spec.pre_transform, "x")
        lines.append(f"    {var} = [{expr} for x in {var}]")
    return lines


def render_most_frequent(
    spec: MostFrequentSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    preprocess = _render_preprocess(spec, var)

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    if not {var}:",
            f"        return {spec.empty_default}",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            (
                "    candidates = [val for val, cnt in counts.items() "
                "if cnt == max_count]"
            ),
        ]
        if spec.tie_default is not None:
            lines.append("    if len(candidates) > 1:")
            lines.append(f"        return {spec.tie_default}")
        lines.append("    return min(candidates)")
    else:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    if not {var}:",
            f"        return {spec.empty_default}",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            (
                "    candidates = [val for val, cnt in counts.items() "
                "if cnt == max_count]"
            ),
        ]
        if spec.tie_default is not None:
            lines.append("    if len(candidates) > 1:")
            lines.append(f"        return {spec.tie_default}")
        lines.extend(
            [
                f"    for x in {var}:",
                "        if x in candidates:",
                "            return x",
                "    return candidates[0]",
            ]
        )
    return "\n".join(lines)


def render_count_pairs_sum(
    spec: CountPairsSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    preprocess = _render_preprocess(spec, var)

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    target = {spec.target}",
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if len({var}) < 2:")
            lines.append(f"        return {spec.short_list_default}")
        lines.extend(
            [
                "    count = 0",
                f"    for i in range(len({var})):",
                f"        for j in range(i + 1, len({var})):",
                f"            if {var}[i] + {var}[j] == target:",
                "                count += 1",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if count == 0:")
            lines.append(f"        return {spec.no_result_default}")
        lines.append("    return count")
    else:
        lines = [
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    target = {spec.target}",
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if len({var}) < 2:")
            lines.append(f"        return {spec.short_list_default}")
        lines.extend(
            [
                "    seen_pairs = set()",
                f"    for i in range(len({var})):",
                f"        for j in range(i + 1, len({var})):",
                f"            if {var}[i] + {var}[j] == target:",
                f"                pair = tuple(sorted([{var}[i], {var}[j]]))",
                "                seen_pairs.add(pair)",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if len(seen_pairs) == 0:")
            lines.append(f"        return {spec.no_result_default}")
        lines.append("    return len(seen_pairs)")
    return "\n".join(lines)


def render_max_window_sum(
    spec: MaxWindowSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    preprocess = _render_preprocess(spec, var)

    lines = [
        f"def {func_name}({var}: list[int]) -> int:",
        *preprocess,
    ]
    if spec.empty_default is not None:
        lines.append(f"    if not {var}:")
        lines.append(f"        return {spec.empty_default}")
    lines.extend(
        [
            f"    if len({var}) < {spec.k}:",
            f"        return {spec.invalid_k_default}",
            "    window_sum = 0",
            f"    for x in {var}[:{spec.k}]:",
            "        window_sum += x",
            "    max_sum = window_sum",
            f"    for i in range({spec.k}, len({var})):",
            f"        window_sum = window_sum - {var}[i - {spec.k}] + {var}[i]",
            "        max_sum = max(max_sum, window_sum)",
            "    return max_sum",
        ]
    )
    return "\n".join(lines)


def render_simple_algorithms(
    spec: SimpleAlgorithmsSpec,
    func_name: str = "f",
    var: str = "xs",
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
