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


def _render_i32_helpers() -> list[str]:
    return [
        "def __i32_wrap(value: int) -> int:",
        "    return ((value + 2147483648) & 0xFFFFFFFF) - 2147483648",
        "",
        "def __i32_add(lhs: int, rhs: int) -> int:",
        "    return __i32_wrap(__i32_wrap(lhs) + __i32_wrap(rhs))",
        "",
        "def __i32_sub(lhs: int, rhs: int) -> int:",
        "    return __i32_wrap(__i32_wrap(lhs) - __i32_wrap(rhs))",
        "",
        "def __i32_mul(lhs: int, rhs: int) -> int:",
        "    return __i32_wrap(__i32_wrap(lhs) * __i32_wrap(rhs))",
        "",
        "def __i32_neg(value: int) -> int:",
        "    return __i32_wrap(-__i32_wrap(value))",
        "",
        "def __i32_abs(value: int) -> int:",
        "    value_i32 = __i32_wrap(value)",
        "    if value_i32 == -2147483648:",
        "        return -2147483648",
        "    return abs(value_i32)",
        "",
        "def __i32_clip(value: int, low: int, high: int) -> int:",
        "    value_i32 = __i32_wrap(value)",
        "    low_i32 = __i32_wrap(low)",
        "    high_i32 = __i32_wrap(high)",
        "    return max(low_i32, min(high_i32, value_i32))",
        "",
        "def __i32_mod(value: int, divisor: int) -> int:",
        "    divisor_i32 = __i32_wrap(divisor)",
        "    if divisor_i32 <= 0:",
        (
            "        raise ValueError('divisor must be in [1, 2147483647] "
            "for int32 semantics')"
        ),
        "    return __i32_wrap(value) % divisor_i32",
        "",
    ]


def _render_preprocess(
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec, var: str
) -> list[str]:
    lines: list[str] = [f"    {var} = [__i32_wrap(x) for x in {var}]"]
    if spec.pre_filter is not None:
        cond = render_predicate(spec.pre_filter, "x", int32_wrap=True)
        lines.append(f"    {var} = [x for x in {var} if {cond}]")
    if spec.pre_transform is not None:
        expr = render_transform(spec.pre_transform, "x", int32_wrap=True)
        lines.append(f"    {var} = [{expr} for x in {var}]")
    return lines


def render_most_frequent(
    spec: MostFrequentSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess(spec, var)

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            *_render_i32_helpers(),
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    if not {var}:",
            f"        return __i32_wrap({spec.empty_default})",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            "    candidates = [val for val, cnt in counts.items() if cnt == max_count]",  # noqa: E501
        ]
        if spec.tie_default is not None:
            lines.append("    if len(candidates) > 1:")
            lines.append(f"        return __i32_wrap({spec.tie_default})")
        lines.append("    return min(candidates)")
    else:
        lines = [
            *_render_i32_helpers(),
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    if not {var}:",
            f"        return __i32_wrap({spec.empty_default})",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            "    candidates = set(val for val, cnt in counts.items() if cnt == max_count)",  # noqa: E501
        ]
        if spec.tie_default is not None:
            lines.append("    if len(candidates) > 1:")
            lines.append(f"        return __i32_wrap({spec.tie_default})")
        lines.extend(
            [
                f"    for x in {var}:",
                "        if x in candidates:",
                "            return x",
                f"    return __i32_wrap({spec.empty_default})",
            ]
        )
    return "\n".join(lines)


def render_count_pairs_sum(
    spec: CountPairsSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess(spec, var)

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            *_render_i32_helpers(),
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    target = __i32_wrap({spec.target})",
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if len({var}) < 2:")
            lines.append(
                f"        return __i32_wrap({spec.short_list_default})"
            )
        lines.extend(
            [
                "    count = 0",
                f"    for i in range(len({var})):",
                f"        for j in range(i + 1, len({var})):",
                "            if __i32_add("
                f"{var}[i], {var}[j]"
                ") == target:",
                "                count = __i32_add(count, 1)",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if count == 0:")
            lines.append(
                f"        return __i32_wrap({spec.no_result_default})"
            )
        lines.append("    return __i32_wrap(count)")
    else:
        lines = [
            *_render_i32_helpers(),
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    target = __i32_wrap({spec.target})",
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if len({var}) < 2:")
            lines.append(
                f"        return __i32_wrap({spec.short_list_default})"
            )
        lines.extend(
            [
                "    seen_pairs = set()",
                f"    for i in range(len({var})):",
                f"        for j in range(i + 1, len({var})):",
                "            if __i32_add("
                f"{var}[i], {var}[j]"
                ") == target:",
                f"                pair = tuple(sorted([{var}[i], {var}[j]]))",  # noqa: E501
                "                seen_pairs.add(pair)",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if len(seen_pairs) == 0:")
            lines.append(
                f"        return __i32_wrap({spec.no_result_default})"
            )
        lines.append("    return __i32_wrap(len(seen_pairs))")
    return "\n".join(lines)


def render_max_window_sum(
    spec: MaxWindowSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess(spec, var)

    lines = [
        *_render_i32_helpers(),
        f"def {func_name}({var}: list[int]) -> int:",
        *preprocess,
    ]
    if spec.empty_default is not None:
        lines.append(f"    if not {var}:")
        lines.append(f"        return __i32_wrap({spec.empty_default})")
    lines.extend(
        [
            f"    if len({var}) < {spec.k}:",
            f"        return __i32_wrap({spec.invalid_k_default})",
            "    window_sum = 0",
            f"    for x in {var}[:{spec.k}]:",
            "        window_sum = __i32_add(window_sum, x)",
            "    max_sum = window_sum",
            f"    for i in range({spec.k}, len({var})):",
            "        window_sum = __i32_add("
            f"__i32_sub(window_sum, {var}[i - {spec.k}]), "
            f"{var}[i]"
            ")",
            "        max_sum = max(max_sum, window_sum)",
            "    return max_sum",
        ]
    )
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
