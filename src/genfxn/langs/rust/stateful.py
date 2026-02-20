from genfxn.langs.rust._helpers import rust_i64_literal
from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.langs.rust.transforms import render_transform_rust
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    ToggleSumSpec,
)


def _i64_expr(value: int) -> str:
    literal = rust_i64_literal(value)
    if literal.endswith("i64"):
        return literal[:-3]
    return literal


def _render_conditional_linear_sum(
    spec: ConditionalLinearSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.predicate, "x")
    true_expr = render_transform_rust(spec.true_transform, "x")
    false_expr = render_transform_rust(spec.false_transform, "x")
    init_value = _i64_expr(spec.init_value)

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        f"    let mut acc: i64 = {init_value};",
        f"    for &x in {var} {{",
        f"        if {cond} {{",
        f"            acc += {true_expr};",
        "        } else {",
        f"            acc += {false_expr};",
        "        }",
        "    }",
        "    acc",
        "}",
    ]
    return "\n".join(lines)


def _render_resetting_best_prefix_sum(
    spec: ResettingBestPrefixSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.reset_predicate, "x")
    val_expr = (
        render_transform_rust(spec.value_transform, "x")
        if spec.value_transform is not None
        else "x"
    )
    init_value = _i64_expr(spec.init_value)

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        f"    let init: i64 = {init_value};",
        "    let mut current_sum: i64 = init;",
        "    let mut best_sum: i64 = init;",
        f"    for &x in {var} {{",
        f"        if {cond} {{",
        "            current_sum = init;",
        "        } else {",
        f"            current_sum += {val_expr};",
        "            best_sum = best_sum.max(current_sum);",
        "        }",
        "    }",
        "    best_sum",
        "}",
    ]
    return "\n".join(lines)


def _render_longest_run(
    spec: LongestRunSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.match_predicate, "x")

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        "    let mut current_run: i64 = 0;",
        "    let mut longest_run: i64 = 0;",
        f"    for &x in {var} {{",
        f"        if {cond} {{",
        "            current_run += 1;",
        "            longest_run = longest_run.max(current_run);",
        "        } else {",
        "            current_run = 0;",
        "        }",
        "    }",
        "    longest_run",
        "}",
    ]
    return "\n".join(lines)


def _render_toggle_sum(
    spec: ToggleSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_rust(spec.toggle_predicate, "x")
    on_expr = render_transform_rust(spec.on_transform, "x")
    off_expr = render_transform_rust(spec.off_transform, "x")
    init_value = _i64_expr(spec.init_value)

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        "    let mut on = false;",
        f"    let mut acc: i64 = {init_value};",
        f"    for &x in {var} {{",
        f"        if {cond} {{",
        "            on = !on;",
        "        }",
        "        if on {",
        f"            acc += {on_expr};",
        "        } else {",
        f"            acc += {off_expr};",
        "        }",
        "    }",
        "    acc",
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
