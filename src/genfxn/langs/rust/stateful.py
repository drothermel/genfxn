from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.langs.rust.transforms import render_transform_rust
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    ToggleSumSpec,
)

_I32_HELPERS = [
    "    fn i32_wrap(value: i64) -> i64 {",
    "        (value as i32) as i64",
    "    }",
    "    fn i32_add(lhs: i64, rhs: i64) -> i64 {",
    "        ((lhs as i32).wrapping_add(rhs as i32)) as i64",
    "    }",
    "    fn i32_mul(lhs: i64, rhs: i64) -> i64 {",
    "        ((lhs as i32).wrapping_mul(rhs as i32)) as i64",
    "    }",
    "    fn i32_neg(value: i64) -> i64 {",
    "        (value as i32).wrapping_neg() as i64",
    "    }",
    "    fn i32_abs(value: i64) -> i64 {",
    "        (value as i32).wrapping_abs() as i64",
    "    }",
    "    fn i32_clip(value: i64, low: i64, high: i64) -> i64 {",
    "        let value_i32 = value as i32;",
    "        let low_i32 = low as i32;",
    "        let high_i32 = high as i32;",
    "        value_i32.max(low_i32).min(high_i32) as i64",
    "    }",
]


def _render_conditional_linear_sum(
    spec: ConditionalLinearSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.predicate, "x")
    true_expr = render_transform_rust(
        spec.true_transform, "x", int32_wrap=True
    )
    false_expr = render_transform_rust(
        spec.false_transform, "x", int32_wrap=True
    )

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        *_I32_HELPERS,
        f"    let mut acc: i64 = i32_wrap({spec.init_value});",
        f"    for &x_raw in {var} {{",
        "        let x = i32_wrap(x_raw);",
        f"        if {cond} {{",
        f"            acc = i32_add(acc, {true_expr});",
        "        } else {",
        f"            acc = i32_add(acc, {false_expr});",
        "        }",
        "    }",
        "    i32_wrap(acc)",
        "}",
    ]
    return "\n".join(lines)


def _render_resetting_best_prefix_sum(
    spec: ResettingBestPrefixSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.reset_predicate, "x")
    val_expr = (
        render_transform_rust(spec.value_transform, "x", int32_wrap=True)
        if spec.value_transform is not None
        else "x"
    )

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        *_I32_HELPERS,
        f"    let init: i64 = i32_wrap({spec.init_value});",
        "    let mut current_sum: i64 = init;",
        "    let mut best_sum: i64 = init;",
        f"    for &x_raw in {var} {{",
        "        let x = i32_wrap(x_raw);",
        f"        if {cond} {{",
        "            current_sum = init;",
        "        } else {",
        f"            current_sum = i32_add(current_sum, {val_expr});",
        "            best_sum = best_sum.max(current_sum);",
        "        }",
        "    }",
        "    i32_wrap(best_sum)",
        "}",
    ]
    return "\n".join(lines)


def _render_longest_run(
    spec: LongestRunSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.match_predicate, "x")

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        *_I32_HELPERS,
        "    let mut current_run: i64 = 0;",
        "    let mut longest_run: i64 = 0;",
        f"    for &x_raw in {var} {{",
        "        let x = i32_wrap(x_raw);",
        f"        if {cond} {{",
        "            current_run = i32_add(current_run, 1);",
        "            longest_run = longest_run.max(current_run);",
        "        } else {",
        "            current_run = 0;",
        "        }",
        "    }",
        "    i32_wrap(longest_run)",
        "}",
    ]
    return "\n".join(lines)


def _render_toggle_sum(
    spec: ToggleSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.toggle_predicate, "x")
    on_expr = render_transform_rust(spec.on_transform, "x", int32_wrap=True)
    off_expr = render_transform_rust(spec.off_transform, "x", int32_wrap=True)

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        *_I32_HELPERS,
        "    let mut on = false;",
        f"    let mut acc: i64 = i32_wrap({spec.init_value});",
        f"    for &x_raw in {var} {{",
        "        let x = i32_wrap(x_raw);",
        f"        if {cond} {{",
        "            on = !on;",
        "        }",
        "        if on {",
        f"            acc = i32_add(acc, {on_expr});",
        "        } else {",
        f"            acc = i32_add(acc, {off_expr});",
        "        }",
        "    }",
        "    i32_wrap(acc)",
        "}",
    ]
    return "\n".join(lines)


def render_stateful(
    spec: StatefulSpec, func_name: str = "f", var: str = "xs"
) -> str:
    """Render a stateful spec as a Rust function."""
    match spec:
        case ConditionalLinearSumSpec():
            return _render_conditional_linear_sum(spec, func_name, var)
        case ResettingBestPrefixSumSpec():
            return _render_resetting_best_prefix_sum(spec, func_name, var)
        case LongestRunSpec():
            return _render_longest_run(spec, func_name, var)
        case ToggleSumSpec():
            return _render_toggle_sum(spec, func_name, var)
        case _:
            raise ValueError(f"Unknown stateful spec: {spec}")
