from genfxn.langs.rust._helpers import rust_i64_literal
from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
)


def _i64_expr(value: int) -> str:
    literal = rust_i64_literal(value)
    if literal.endswith("i64"):
        return literal[:-3]
    return literal


def _render_linear_i32(a: int, x_term: str, b: int) -> str:
    ax = "0" if a == 0 else f"i32_mul({_i64_expr(a)}, {x_term})"
    if b == 0:
        return ax
    return f"i32_add({ax}, {_i64_expr(b)})"


def _render_quadratic_i32(a: int, b: int, c: int, var: str) -> str:
    acc = "0"

    if a != 0:
        ra = _i64_expr(a)
        acc = f"i32_mul(i32_mul({ra}, {var}), {var})"

    if b != 0:
        bx = f"i32_mul({_i64_expr(b)}, {var})"
        if acc == "0":
            acc = bx
        else:
            acc = f"i32_add({acc}, {bx})"

    if c != 0:
        if acc == "0":
            acc = f"i32_wrap({_i64_expr(c)})"
        else:
            acc = f"i32_add({acc}, {_i64_expr(c)})"

    return acc


def render_expression_rust(
    expr: Expression,
    var: str = "x",
    *,
    int32_wrap: bool = False,
) -> str:
    """Render a piecewise expression as a Rust expression."""
    if int32_wrap:
        match expr:
            case ExprAffine(a=a, b=b):
                return _render_linear_i32(a, var, b)
            case ExprQuadratic(a=a, b=b, c=c):
                return _render_quadratic_i32(a, b, c, var)
            case ExprAbs(a=a, b=b):
                return _render_linear_i32(a, f"i32_abs({var})", b)
            case ExprMod(divisor=d, a=a, b=b):
                return _render_linear_i32(a, f"i32_mod({var}, {d})", b)
            case _:
                raise ValueError(f"Unknown expression: {expr}")

    match expr:
        case ExprAffine(a=a, b=b):
            return _render_linear(a, var, b)
        case ExprQuadratic(a=a, b=b, c=c):
            return _render_quadratic(a, b, c, var)
        case ExprAbs(a=a, b=b):
            return _render_linear(a, f"{var}.abs()", b)
        case ExprMod(divisor=d, a=a, b=b):
            return _render_linear(a, f"{var}.rem_euclid({d})", b)
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def _render_linear(a: int, x_term: str, b: int) -> str:
    if a == 0:
        return _i64_expr(b)
    if a == 1:
        ax = x_term
    elif a == -1:
        ax = f"-{x_term}"
    else:
        ax = f"{_i64_expr(a)} * {x_term}"

    if b == 0:
        return ax
    if b > 0:
        return f"{ax} + {_i64_expr(b)}"
    return f"{ax} - {_i64_expr(-b)}"


def _render_quadratic(a: int, b: int, c: int, var: str) -> str:
    parts: list[str] = []

    if a != 0:
        if a == 1:
            parts.append(f"{var} * {var}")
        elif a == -1:
            parts.append(f"-{var} * {var}")
        else:
            parts.append(f"{_i64_expr(a)} * {var} * {var}")

    if b != 0:
        abs_term = (
            var
            if abs(b) == 1
            else f"{_i64_expr(abs(b))} * {var}"
        )

        if not parts:
            parts.append(f"-{abs_term}" if b < 0 else abs_term)
        elif b > 0:
            parts.append(f" + {abs_term}")
        else:
            parts.append(f" - {abs_term}")

    if c != 0:
        if parts and c > 0:
            parts.append(f" + {_i64_expr(c)}")
        elif parts and c < 0:
            parts.append(f" - {_i64_expr(-c)}")
        else:
            parts.append(_i64_expr(c))

    if not parts:
        return "0"

    return "".join(parts)
