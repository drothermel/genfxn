from genfxn.core.predicates import render_predicate
from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
    PiecewiseSpec,
)


def _render_i32_helpers() -> list[str]:
    return [
        "def __i32_wrap(value: int) -> int:",
        "    return ((value + 2147483648) & 0xFFFFFFFF) - 2147483648",
        "",
        "def __i32_add(lhs: int, rhs: int) -> int:",
        "    return __i32_wrap(__i32_wrap(lhs) + __i32_wrap(rhs))",
        "",
        "def __i32_mul(lhs: int, rhs: int) -> int:",
        "    return __i32_wrap(__i32_wrap(lhs) * __i32_wrap(rhs))",
        "",
        "def __i32_abs(value: int) -> int:",
        "    value_i32 = __i32_wrap(value)",
        "    if value_i32 == -2147483648:",
        "        return -2147483648",
        "    return abs(value_i32)",
        "",
        "def __i32_mod(value: int, divisor: int) -> int:",
        "    divisor_i32 = __i32_wrap(divisor)",
        "    if divisor_i32 <= 0:",
        (
            "        raise ValueError('divisor must be in [1, 2147483647] "
            "for int32 semantics')"
        ),
        "    return __i32_wrap(value) % divisor_i32",
        "",
    ]


def render_expression(
    expr: Expression,
    var: str = "x",
    *,
    int32_wrap: bool = False,
) -> str:
    if int32_wrap:
        match expr:
            case ExprAffine(a=a, b=b):
                return _render_linear_i32(a, var, b)
            case ExprQuadratic(a=a, b=b, c=c):
                return _render_quadratic_i32(a, b, c, var)
            case ExprAbs(a=a, b=b):
                return _render_linear_i32(a, f"__i32_abs({var})", b)
            case ExprMod(divisor=d, a=a, b=b):
                return _render_linear_i32(a, f"__i32_mod({var}, {d})", b)
            case _:
                raise ValueError(f"Unknown expression: {expr}")

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


def _render_linear_i32(a: int, x_term: str, b: int) -> str:
    ax = "0" if a == 0 else f"__i32_mul({a}, {x_term})"
    if b == 0:
        return ax
    return f"__i32_add({ax}, {b})"


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


def _render_quadratic_i32(a: int, b: int, c: int, var: str) -> str:
    acc = "0"

    if a != 0:
        acc = f"__i32_mul(__i32_mul({a}, {var}), {var})"

    if b != 0:
        bx = f"__i32_mul({b}, {var})"
        if acc == "0":
            acc = bx
        else:
            acc = f"__i32_add({acc}, {bx})"

    if c != 0:
        if acc == "0":
            acc = f"__i32_wrap({c})"
        else:
            acc = f"__i32_add({acc}, {c})"

    return acc


def render_piecewise(
    spec: PiecewiseSpec,
    func_name: str = "f",
    var: str = "x",
    *,
    int32_wrap: bool = True,
) -> str:
    lines: list[str] = []
    if int32_wrap:
        lines.extend(_render_i32_helpers())
    lines.append(f"def {func_name}({var}: int) -> int:")

    for i, branch in enumerate(spec.branches):
        keyword = "if" if i == 0 else "elif"
        cond = render_predicate(
            branch.condition,
            var,
            int32_wrap=int32_wrap,
        )
        expr = render_expression(
            branch.expr,
            var,
            int32_wrap=int32_wrap,
        )
        lines.append(f"    {keyword} {cond}:")
        lines.append(f"        return {expr}")

    default_expr = render_expression(
        spec.default_expr,
        var,
        int32_wrap=int32_wrap,
    )
    if spec.branches:
        lines.append("    else:")
        lines.append(f"        return {default_expr}")
    else:
        lines.append(f"    return {default_expr}")

    return "\n".join(lines)
