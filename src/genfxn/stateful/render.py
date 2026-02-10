from genfxn.core.predicates import render_predicate
from genfxn.core.transforms import render_transform
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    ToggleSumSpec,
)


def _render_i32_helpers() -> list[str]:
    return [
        "def __i32_wrap(value: int) -> int:",
        "    return ((value + 2147483648) & 0xFFFFFFFF) - 2147483648",
        "",
        "def __i32_add(lhs: int, rhs: int) -> int:",
        "    return __i32_wrap(__i32_wrap(lhs) + __i32_wrap(rhs))",
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


def render_conditional_linear_sum(
    spec: ConditionalLinearSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate(spec.predicate, "x", int32_wrap=True)
    true_expr = render_transform(spec.true_transform, "x", int32_wrap=True)
    false_expr = render_transform(
        spec.false_transform, "x", int32_wrap=True
    )

    lines = [
        *_render_i32_helpers(),
        f"def {func_name}({var}: list[int]) -> int:",
        f"    acc = __i32_wrap({spec.init_value})",
        f"    for x in {var}:",
        "        x = __i32_wrap(x)",
        f"        if {cond}:",
        f"            acc = __i32_add(acc, {true_expr})",
        "        else:",
        f"            acc = __i32_add(acc, {false_expr})",
        "    return acc",
    ]
    return "\n".join(lines)


def render_resetting_best_prefix_sum(
    spec: ResettingBestPrefixSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate(spec.reset_predicate, "x", int32_wrap=True)
    val_expr = (
        render_transform(spec.value_transform, "x", int32_wrap=True)
        if spec.value_transform is not None
        else "x"
    )

    lines = [
        *_render_i32_helpers(),
        f"def {func_name}({var}: list[int]) -> int:",
        f"    init = __i32_wrap({spec.init_value})",
        "    current_sum = init",
        "    best_sum = init",
        f"    for x in {var}:",
        "        x = __i32_wrap(x)",
        f"        if {cond}:",
        "            current_sum = init",
        "        else:",
        f"            current_sum = __i32_add(current_sum, {val_expr})",
        "            best_sum = max(best_sum, current_sum)",
        "    return best_sum",
    ]
    return "\n".join(lines)


def render_longest_run(
    spec: LongestRunSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate(spec.match_predicate, "x", int32_wrap=True)

    lines = [
        *_render_i32_helpers(),
        f"def {func_name}({var}: list[int]) -> int:",
        "    current_run = 0",
        "    longest_run = 0",
        f"    for x in {var}:",
        "        x = __i32_wrap(x)",
        f"        if {cond}:",
        "            current_run = __i32_add(current_run, 1)",
        "            longest_run = max(longest_run, current_run)",
        "        else:",
        "            current_run = 0",
        "    return longest_run",
    ]
    return "\n".join(lines)


def render_toggle_sum(
    spec: ToggleSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate(spec.toggle_predicate, "x", int32_wrap=True)
    on_expr = render_transform(spec.on_transform, "x", int32_wrap=True)
    off_expr = render_transform(spec.off_transform, "x", int32_wrap=True)

    lines = [
        *_render_i32_helpers(),
        f"def {func_name}({var}: list[int]) -> int:",
        "    on = False",
        f"    acc = __i32_wrap({spec.init_value})",
        f"    for x in {var}:",
        "        x = __i32_wrap(x)",
        f"        if {cond}:",
        "            on = not on",
        "        if on:",
        f"            acc = __i32_add(acc, {on_expr})",
        "        else:",
        f"            acc = __i32_add(acc, {off_expr})",
        "    return acc",
    ]
    return "\n".join(lines)


def render_stateful(
    spec: StatefulSpec, func_name: str = "f", var: str = "xs"
) -> str:
    match spec:
        case ConditionalLinearSumSpec():
            return render_conditional_linear_sum(spec, func_name, var)
        case ResettingBestPrefixSumSpec():
            return render_resetting_best_prefix_sum(spec, func_name, var)
        case LongestRunSpec():
            return render_longest_run(spec, func_name, var)
        case ToggleSumSpec():
            return render_toggle_sum(spec, func_name, var)
        case _:
            raise ValueError(f"Unknown stateful spec: {spec}")
