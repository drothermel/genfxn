from genfxn.langs.java.predicates import render_predicate_java
from genfxn.langs.java.transforms import render_transform_java
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    ToggleSumSpec,
)


def _render_conditional_linear_sum(
    spec: ConditionalLinearSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_java(spec.predicate, "x")
    true_expr = render_transform_java(spec.true_transform, "x")
    false_expr = render_transform_java(spec.false_transform, "x")

    lines = [
        f"public static int {func_name}(int[] {var}) {{",
        f"    int acc = {spec.init_value};",
        f"    for (int x : {var}) {{",
        f"        if ({cond}) {{",
        f"            acc += {true_expr};",
        "        } else {",
        f"            acc += {false_expr};",
        "        }",
        "    }",
        "    return acc;",
        "}",
    ]
    return "\n".join(lines)


def _render_resetting_best_prefix_sum(
    spec: ResettingBestPrefixSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_java(spec.reset_predicate, "x")
    val_expr = (
        render_transform_java(spec.value_transform, "x")
        if spec.value_transform is not None
        else "x"
    )

    lines = [
        f"public static int {func_name}(int[] {var}) {{",
        f"    int current_sum = {spec.init_value};",
        f"    int best_sum = {spec.init_value};",
        f"    for (int x : {var}) {{",
        f"        if ({cond}) {{",
        f"            current_sum = {spec.init_value};",
        "        } else {",
        f"            current_sum += {val_expr};",
        "            best_sum = Math.max(best_sum, current_sum);",
        "        }",
        "    }",
        "    return best_sum;",
        "}",
    ]
    return "\n".join(lines)


def _render_longest_run(
    spec: LongestRunSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_java(spec.match_predicate, "x")

    lines = [
        f"public static int {func_name}(int[] {var}) {{",
        "    int current_run = 0;",
        "    int longest_run = 0;",
        f"    for (int x : {var}) {{",
        f"        if ({cond}) {{",
        "            current_run += 1;",
        "            longest_run = Math.max(longest_run, current_run);",
        "        } else {",
        "            current_run = 0;",
        "        }",
        "    }",
        "    return longest_run;",
        "}",
    ]
    return "\n".join(lines)


def _render_toggle_sum(
    spec: ToggleSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    cond = render_predicate_java(spec.toggle_predicate, "x")
    on_expr = render_transform_java(spec.on_transform, "x")
    off_expr = render_transform_java(spec.off_transform, "x")

    lines = [
        f"public static int {func_name}(int[] {var}) {{",
        "    boolean on = false;",
        f"    int acc = {spec.init_value};",
        f"    for (int x : {var}) {{",
        f"        if ({cond}) {{",
        "            on = !on;",
        "        }",
        "        if (on) {",
        f"            acc += {on_expr};",
        "        } else {",
        f"            acc += {off_expr};",
        "        }",
        "    }",
        "    return acc;",
        "}",
    ]
    return "\n".join(lines)


def render_stateful(
    spec: StatefulSpec, func_name: str = "f", var: str = "xs"
) -> str:
    """Render a stateful spec as a Java static method."""
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
