from genfxn.langs.java._helpers import java_int_literal
from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
)


def render_expression_java(expr: Expression, var: str = "x") -> str:
    """Render a piecewise expression as a Java expression."""
    match expr:
        case ExprAffine(a=a, b=b):
            return _render_linear(a, var, b)
        case ExprQuadratic(a=a, b=b, c=c):
            return _render_quadratic(a, b, c, var)
        case ExprAbs(a=a, b=b):
            return _render_linear(a, f"Math.abs({var})", b)
        case ExprMod(divisor=d, a=a, b=b):
            divisor = java_int_literal(d)
            return _render_linear(a, f"Math.floorMod({var}, {divisor})", b)
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def _render_linear(a: int, x_term: str, b: int) -> str:
    if a == 0:
        return java_int_literal(b)
    if a == 1:
        ax = x_term
    elif a == -1:
        ax = f"-{x_term}"
    else:
        ax = f"{java_int_literal(a)} * {x_term}"

    if b == 0:
        return ax
    if b > 0:
        return f"{ax} + {java_int_literal(b)}"
    return f"{ax} - {java_int_literal(-b)}"


def _render_quadratic(a: int, b: int, c: int, var: str) -> str:
    parts: list[str] = []

    if a != 0:
        if a == 1:
            parts.append(f"{var} * {var}")
        elif a == -1:
            parts.append(f"-{var} * {var}")
        else:
            parts.append(f"{java_int_literal(a)} * {var} * {var}")

    if b != 0:
        abs_b = abs(b)
        abs_term = (
            var
            if abs_b == 1
            else f"{java_int_literal(abs_b)} * {var}"
        )

        if not parts:
            parts.append(f"-{abs_term}" if b < 0 else abs_term)
        elif b > 0:
            parts.append(f" + {abs_term}")
        else:
            parts.append(f" - {abs_term}")

    if c != 0:
        if parts and c > 0:
            parts.append(f" + {java_int_literal(c)}")
        elif parts and c < 0:
            parts.append(f" - {java_int_literal(-c)}")
        else:
            parts.append(java_int_literal(c))

    if not parts:
        return "0"

    return "".join(parts)
