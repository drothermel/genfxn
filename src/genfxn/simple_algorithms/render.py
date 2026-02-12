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
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec,
    var: str,
    *,
    int32_wrap: bool,
) -> list[str]:
    lines: list[str] = []
    if int32_wrap:
        lines.append(f"    {var} = [__i32_wrap(x) for x in {var}]")
    if spec.pre_filter is not None:
        cond = render_predicate(spec.pre_filter, "x", int32_wrap=int32_wrap)
        lines.append(f"    {var} = [x for x in {var} if {cond}]")
    if spec.pre_transform is not None:
        expr = render_transform(spec.pre_transform, "x", int32_wrap=int32_wrap)
        lines.append(f"    {var} = [{expr} for x in {var}]")
    return lines


def _wrap_literal(value: int, *, int32_wrap: bool) -> str:
    if int32_wrap:
        return f"__i32_wrap({value})"
    return str(value)


def render_most_frequent(
    spec: MostFrequentSpec,
    func_name: str = "f",
    var: str = "xs",
    *,
    int32_wrap: bool = True,
) -> str:
    preprocess = _render_preprocess(spec, var, int32_wrap=int32_wrap)
    prelude = _render_i32_helpers() if int32_wrap else []
    empty_default = _wrap_literal(spec.empty_default, int32_wrap=int32_wrap)

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            *prelude,
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    if not {var}:",
            f"        return {empty_default}",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            "    candidates = [val for val, cnt in counts.items() if cnt == max_count]",  # noqa: E501
        ]
        if spec.tie_default is not None:
            lines.append("    if len(candidates) > 1:")
            tie_default = _wrap_literal(spec.tie_default, int32_wrap=int32_wrap)
            lines.append(f"        return {tie_default}")
        lines.append("    return min(candidates)")
    else:
        lines = [
            *prelude,
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    if not {var}:",
            f"        return {empty_default}",
            "    counts = {}",
            f"    for x in {var}:",
            "        counts[x] = counts.get(x, 0) + 1",
            "    max_count = max(counts.values())",
            "    candidates = set(val for val, cnt in counts.items() if cnt == max_count)",  # noqa: E501
        ]
        if spec.tie_default is not None:
            lines.append("    if len(candidates) > 1:")
            tie_default = _wrap_literal(spec.tie_default, int32_wrap=int32_wrap)
            lines.append(f"        return {tie_default}")
        lines.extend(
            [
                f"    for x in {var}:",
                "        if x in candidates:",
                "            return x",
                f"    return {empty_default}",
            ]
        )
    return "\n".join(lines)


def render_count_pairs_sum(
    spec: CountPairsSumSpec,
    func_name: str = "f",
    var: str = "xs",
    *,
    int32_wrap: bool = True,
) -> str:
    preprocess = _render_preprocess(spec, var, int32_wrap=int32_wrap)
    prelude = _render_i32_helpers() if int32_wrap else []
    target = _wrap_literal(spec.target, int32_wrap=int32_wrap)

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            *prelude,
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    target = {target}",
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if len({var}) < 2:")
            short_default = _wrap_literal(
                spec.short_list_default,
                int32_wrap=int32_wrap,
            )
            lines.append(f"        return {short_default}")
        sum_expr = (
            f"__i32_add({var}[i], {var}[j])"
            if int32_wrap
            else f"{var}[i] + {var}[j]"
        )
        count_increment = (
            "count = __i32_add(count, 1)" if int32_wrap else "count += 1"
        )
        lines.extend(
            [
                "    count = 0",
                f"    for i in range(len({var})):",
                f"        for j in range(i + 1, len({var})):",
                f"            if {sum_expr} == target:",
                f"                {count_increment}",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if count == 0:")
            no_result = _wrap_literal(
                spec.no_result_default,
                int32_wrap=int32_wrap,
            )
            lines.append(f"        return {no_result}")
        lines.append(
            "    return __i32_wrap(count)" if int32_wrap else "    return count"
        )
    else:
        lines = [
            *prelude,
            f"def {func_name}({var}: list[int]) -> int:",
            *preprocess,
            f"    target = {target}",
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if len({var}) < 2:")
            short_default = _wrap_literal(
                spec.short_list_default,
                int32_wrap=int32_wrap,
            )
            lines.append(f"        return {short_default}")
        sum_expr = (
            f"__i32_add({var}[i], {var}[j])"
            if int32_wrap
            else f"{var}[i] + {var}[j]"
        )
        lines.extend(
            [
                "    seen_pairs = set()",
                f"    for i in range(len({var})):",
                f"        for j in range(i + 1, len({var})):",
                f"            if {sum_expr} == target:",
                f"                pair = tuple(sorted([{var}[i], {var}[j]]))",
                "                seen_pairs.add(pair)",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if len(seen_pairs) == 0:")
            no_result = _wrap_literal(
                spec.no_result_default,
                int32_wrap=int32_wrap,
            )
            lines.append(f"        return {no_result}")
        if int32_wrap:
            lines.append("    return __i32_wrap(len(seen_pairs))")
        else:
            lines.append("    return len(seen_pairs)")
    return "\n".join(lines)


def render_max_window_sum(
    spec: MaxWindowSumSpec,
    func_name: str = "f",
    var: str = "xs",
    *,
    int32_wrap: bool = True,
) -> str:
    preprocess = _render_preprocess(spec, var, int32_wrap=int32_wrap)
    prelude = _render_i32_helpers() if int32_wrap else []

    lines = [
        *prelude,
        f"def {func_name}({var}: list[int]) -> int:",
        *preprocess,
    ]
    if spec.empty_default is not None:
        empty_default = _wrap_literal(spec.empty_default, int32_wrap=int32_wrap)
        lines.append(f"    if not {var}:")
        lines.append(f"        return {empty_default}")
    invalid_default = _wrap_literal(
        spec.invalid_k_default,
        int32_wrap=int32_wrap,
    )
    lines.extend(
        [
            f"    if len({var}) < {spec.k}:",
            f"        return {invalid_default}",
            "    window_sum = 0",
            f"    for x in {var}[:{spec.k}]:",
        ]
    )
    if int32_wrap:
        lines.append("        window_sum = __i32_add(window_sum, x)")
    else:
        lines.append("        window_sum += x")
    lines.extend(
        [
            "    max_sum = window_sum",
            f"    for i in range({spec.k}, len({var})):",
        ]
    )
    if int32_wrap:
        lines.extend(
            [
                "        window_sum = __i32_add("
                f"__i32_sub(window_sum, {var}[i - {spec.k}]), "
                f"{var}[i]"
                ")",
            ]
        )
    else:
        lines.extend(
            [
                "        window_sum = window_sum "
                f"- {var}[i - {spec.k}] + {var}[i]",
            ]
        )
    lines.extend(
        [
            "        max_sum = max(max_sum, window_sum)",
            "    return max_sum",
        ]
    )
    return "\n".join(lines)


def render_simple_algorithms(
    spec: SimpleAlgorithmsSpec,
    func_name: str = "f",
    var: str = "xs",
    *,
    int32_wrap: bool = True,
) -> str:
    match spec:
        case MostFrequentSpec():
            return render_most_frequent(
                spec,
                func_name,
                var,
                int32_wrap=int32_wrap,
            )
        case CountPairsSumSpec():
            return render_count_pairs_sum(
                spec,
                func_name,
                var,
                int32_wrap=int32_wrap,
            )
        case MaxWindowSumSpec():
            return render_max_window_sum(
                spec,
                func_name,
                var,
                int32_wrap=int32_wrap,
            )
        case _:
            raise ValueError(f"Unknown simple algorithms spec: {spec}")
