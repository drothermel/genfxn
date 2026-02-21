from genfxn.core.predicates import render_predicate
from genfxn.core.transforms import render_transform
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    ToggleSumSpec,
)


def render_conditional_linear_sum(
    spec: ConditionalLinearSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    cond = render_predicate(spec.predicate, "x")
    true_expr = render_transform(spec.true_transform, "x")
    false_expr = render_transform(spec.false_transform, "x")

    lines = [
        f"def {func_name}({var}: list[int]) -> int:",
        f"    acc = {spec.init_value}",
        f"    for x in {var}:",
        f"        if {cond}:",
        f"            acc = acc + ({true_expr})",
        "        else:",
        f"            acc = acc + ({false_expr})",
        "    return acc",
    ]
    return "\n".join(lines)


def render_resetting_best_prefix_sum(
    spec: ResettingBestPrefixSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    cond = render_predicate(spec.reset_predicate, "x")
    val_expr = (
        render_transform(spec.value_transform, "x")
        if spec.value_transform is not None
        else "x"
    )

    lines = [
        f"def {func_name}({var}: list[int]) -> int:",
        f"    init = {spec.init_value}",
        "    current_sum = init",
        "    best_sum = init",
        f"    for x in {var}:",
        f"        if {cond}:",
        "            current_sum = init",
        "        else:",
        f"            current_sum = current_sum + ({val_expr})",
        "            best_sum = max(best_sum, current_sum)",
        "    return best_sum",
    ]
    return "\n".join(lines)


def render_longest_run(
    spec: LongestRunSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    cond = render_predicate(spec.match_predicate, "x")

    lines = [
        f"def {func_name}({var}: list[int]) -> int:",
        "    current_run = 0",
        "    longest_run = 0",
        f"    for x in {var}:",
        f"        if {cond}:",
        "            current_run += 1",
        "            longest_run = max(longest_run, current_run)",
        "        else:",
        "            current_run = 0",
        "    return longest_run",
    ]
    return "\n".join(lines)


def render_toggle_sum(
    spec: ToggleSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    cond = render_predicate(spec.toggle_predicate, "x")
    on_expr = render_transform(spec.on_transform, "x")
    off_expr = render_transform(spec.off_transform, "x")

    lines = [
        f"def {func_name}({var}: list[int]) -> int:",
        "    on = False",
        f"    acc = {spec.init_value}",
        f"    for x in {var}:",
        f"        if {cond}:",
        "            on = not on",
        "        if on:",
        f"            acc = acc + ({on_expr})",
        "        else:",
        f"            acc = acc + ({off_expr})",
        "    return acc",
    ]
    return "\n".join(lines)


def render_stateful(
    spec: StatefulSpec,
    func_name: str = "f",
    var: str = "xs",
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
