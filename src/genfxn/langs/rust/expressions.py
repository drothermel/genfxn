from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    ExprMod,
    ExprQuadratic,
    Expression,
)


def render_expression_rust(expr: Expression, var: str = "x") -> str:
    """Render a piecewise expression as a Rust expression."""
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
    parts: list[str] = []

    if a != 0:
        if a == 1:
            parts.append(f"{var} * {var}")
        elif a == -1:
            parts.append(f"-{var} * {var}")
        else:
            parts.append(f"{a} * {var} * {var}")

    if b != 0:
        abs_term = var if abs(b) == 1 else f"{abs(b)} * {var}"

        if not parts:
            parts.append(f"-{abs_term}" if b < 0 else abs_term)
        elif b > 0:
            parts.append(f" + {abs_term}")
        else:
            parts.append(f" - {abs_term}")

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
