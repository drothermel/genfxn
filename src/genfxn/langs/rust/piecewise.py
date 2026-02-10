from genfxn.langs.rust.expressions import render_expression_rust
from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.piecewise.models import PiecewiseSpec


def render_piecewise(
    spec: PiecewiseSpec, func_name: str = "f", var: str = "x"
) -> str:
    """Render a piecewise spec as a Rust function."""
    lines = [
        f"fn {func_name}({var}: i64) -> i64 {{",
        "    fn i32_wrap(value: i64) -> i64 {",
        "        (value as i32) as i64",
        "    }",
        "    fn i32_add(lhs: i64, rhs: i64) -> i64 {",
        "        ((lhs as i32).wrapping_add(rhs as i32)) as i64",
        "    }",
        "    fn i32_mul(lhs: i64, rhs: i64) -> i64 {",
        "        ((lhs as i32).wrapping_mul(rhs as i32)) as i64",
        "    }",
        "    fn i32_abs(value: i64) -> i64 {",
        "        (value as i32).wrapping_abs() as i64",
        "    }",
        "    fn i32_mod(value: i64, divisor: i64) -> i64 {",
        "        ((value as i32).rem_euclid(divisor as i32)) as i64",
        "    }",
        f"    let {var} = i32_wrap({var});",
    ]

    for i, branch in enumerate(spec.branches):
        keyword = "if" if i == 0 else "} else if"
        cond = render_predicate_rust(
            branch.condition, var, int32_wrap=True
        )
        expr = render_expression_rust(branch.expr, var, int32_wrap=True)
        lines.append(f"    {keyword} {cond} {{")
        lines.append(f"        {expr}")

    default_expr = render_expression_rust(
        spec.default_expr, var, int32_wrap=True
    )
    if spec.branches:
        lines.append("    } else {")
        lines.append(f"        {default_expr}")
        lines.append("    }")
    else:
        lines.append(f"    {default_expr}")

    lines.append("}")
    return "\n".join(lines)
