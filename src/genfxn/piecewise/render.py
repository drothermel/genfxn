from genfxn.core.predicates import render_predicate
from genfxn.piecewise.models import (
    Branch,
    ExprAbs,
    ExprAffine,
    ExprMod,
    ExprQuadratic,
    Expression,
    PiecewiseSpec,
)


def render_expression(expr: Expression, var: str = "x") -> str:
    match expr:
        case ExprAffine(a=a, b=b):
            return _render_linear(a, var, b)
        case ExprQuadratic(a=a, b=b, c=c):
            return _render_quadratic(a, b, c, var)
        case ExprAbs(a=a, b=b):
            return _render_linear(a, f"abs({var})", b)
        case ExprMod(divisor=d, a=a, b=b):
            return _render_linear(a, f"({var} % {d})", b)
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def _render_linear(a: int, x_term: str, b: int) -> str:
    if a == 0:
        return str(b)
    if a == 1:
        ax = x_term
    elif a == -1:
        ax = f"-{x_term}"
    else:
        ax = f"{a} * {x_term}"

    if b == 0:
        return ax
    if b > 0:
        return f"{ax} + {b}"
    return f"{ax} - {-b}"


def _render_quadratic(a: int, b: int, c: int, var: str) -> str:
    parts = []

    if a != 0:
        if a == 1:
            parts.append(f"{var} * {var}")
        elif a == -1:
            parts.append(f"-{var} * {var}")
        else:
            parts.append(f"{a} * {var} * {var}")

    if b != 0:
        if b == 1:
            term = var
        elif b == -1:
            term = f"-{var}"
        else:
            term = f"{b} * {var}"

        if parts and b > 0:
            parts.append(f" + {term}")
        elif parts and b < 0:
            parts.append(f" - {-b} * {var}" if b != -1 else f" - {var}")
        else:
            parts.append(term)

    if c != 0:
        if parts and c > 0:
            parts.append(f" + {c}")
        elif parts and c < 0:
            parts.append(f" - {-c}")
        else:
            parts.append(str(c))

    if not parts:
        return "0"

    return "".join(parts)


def render_piecewise(spec: PiecewiseSpec, func_name: str = "f", var: str = "x") -> str:
    lines = [f"def {func_name}({var}: int) -> int:"]

    for i, branch in enumerate(spec.branches):
        keyword = "if" if i == 0 else "elif"
        cond = render_predicate(branch.condition, var)
        expr = render_expression(branch.expr, var)
        lines.append(f"    {keyword} {cond}:")
        lines.append(f"        return {expr}")

    default_expr = render_expression(spec.default_expr, var)
    if spec.branches:
        lines.append("    else:")
        lines.append(f"        return {default_expr}")
    else:
        lines.append(f"    return {default_expr}")

    return "\n".join(lines)
