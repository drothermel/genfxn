from genfxn.langs.rust.expressions import render_expression_rust
from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.piecewise.models import PiecewiseSpec


def render_piecewise(
    spec: PiecewiseSpec, func_name: str = "f", var: str = "x"
) -> str:
    """Render a piecewise spec as a Rust function."""
    lines = [f"fn {func_name}({var}: i64) -> i64 {{"]

    for i, branch in enumerate(spec.branches):
        keyword = "if" if i == 0 else "} else if"
        cond = render_predicate_rust(branch.condition, var)
        expr = render_expression_rust(branch.expr, var)
        lines.append(f"    {keyword} {cond} {{")
        lines.append(f"        {expr}")

    default_expr = render_expression_rust(spec.default_expr, var)
    if spec.branches:
        lines.append("    } else {")
        lines.append(f"        {default_expr}")
        lines.append("    }")
    else:
        lines.append(f"    {default_expr}")

    lines.append("}")
    return "\n".join(lines)
