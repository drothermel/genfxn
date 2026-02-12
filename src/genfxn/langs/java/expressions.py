from genfxn.langs.java._helpers import java_int_literal
from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
)


def _java_literal(value: int, *, int32_wrap: bool) -> str:
    _ = int32_wrap
    return java_int_literal(value)


def render_expression_java(
    expr: Expression,
    var: str = "x",
    *,
    int32_wrap: bool = False,
) -> str:
    """Render a piecewise expression as a Java expression."""
    match expr:
        case ExprAffine(a=a, b=b):
            return _render_linear(a, var, b, int32_wrap=int32_wrap)
        case ExprQuadratic(a=a, b=b, c=c):
            return _render_quadratic(a, b, c, var, int32_wrap=int32_wrap)
        case ExprAbs(a=a, b=b):
            return _render_linear(
                a,
                f"Math.abs({var})",
                b,
                int32_wrap=int32_wrap,
            )
        case ExprMod(divisor=d, a=a, b=b):
            divisor = _java_literal(d, int32_wrap=int32_wrap)
            return _render_linear(
                a,
                f"Math.floorMod({var}, {divisor})",
                b,
                int32_wrap=int32_wrap,
            )
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def _render_linear(
    a: int,
    x_term: str,
    b: int,
    *,
    int32_wrap: bool,
) -> str:
    if a == 0:
        return _java_literal(b, int32_wrap=int32_wrap)
    if a == 1:
        ax = x_term
    elif a == -1:
        ax = f"-{x_term}"
    else:
        ax = f"{_java_literal(a, int32_wrap=int32_wrap)} * {x_term}"

    if b == 0:
        return ax
    if b > 0:
        return f"{ax} + {_java_literal(b, int32_wrap=int32_wrap)}"
    return f"{ax} - {_java_literal(-b, int32_wrap=int32_wrap)}"


def _render_quadratic(
    a: int,
    b: int,
    c: int,
    var: str,
    *,
    int32_wrap: bool,
) -> str:
    parts: list[str] = []

    if a != 0:
        if a == 1:
            parts.append(f"{var} * {var}")
        elif a == -1:
            parts.append(f"-{var} * {var}")
        else:
            literal = _java_literal(a, int32_wrap=int32_wrap)
            parts.append(f"{literal} * {var} * {var}")

    if b != 0:
        abs_b = abs(b)
        abs_term = (
            var
            if abs_b == 1
            else f"{_java_literal(abs_b, int32_wrap=int32_wrap)} * {var}"
        )

        if not parts:
            parts.append(f"-{abs_term}" if b < 0 else abs_term)
        elif b > 0:
            parts.append(f" + {abs_term}")
        else:
            parts.append(f" - {abs_term}")

    if c != 0:
        if parts and c > 0:
            literal = _java_literal(c, int32_wrap=int32_wrap)
            parts.append(f" + {literal}")
        elif parts and c < 0:
            literal = _java_literal(-c, int32_wrap=int32_wrap)
            parts.append(f" - {literal}")
        else:
            parts.append(_java_literal(c, int32_wrap=int32_wrap))

    if not parts:
        return "0"

    return "".join(parts)
