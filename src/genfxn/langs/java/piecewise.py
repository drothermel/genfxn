from genfxn.langs.java.expressions import render_expression_java
from genfxn.langs.java.predicates import render_predicate_java
from genfxn.piecewise.models import PiecewiseSpec


def render_piecewise(
    spec: PiecewiseSpec, func_name: str = "f", var: str = "x"
) -> str:
    """Render a piecewise spec as a Java static method."""
    lines = [f"public static int {func_name}(int {var}) {{"]

    for i, branch in enumerate(spec.branches):
        keyword = "if" if i == 0 else "} else if"
        cond = render_predicate_java(
            branch.condition, var, int32_wrap=True
        )
        expr = render_expression_java(branch.expr, var)
        lines.append(f"    {keyword} ({cond}) {{")
        lines.append(f"        return {expr};")

    default_expr = render_expression_java(spec.default_expr, var)
    if spec.branches:
        lines.append("    } else {")
        lines.append(f"        return {default_expr};")
        lines.append("    }")
    else:
        lines.append(f"    return {default_expr};")

    lines.append("}")
    return "\n".join(lines)
