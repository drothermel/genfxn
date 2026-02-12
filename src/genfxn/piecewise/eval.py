from genfxn.core.int32 import i32_abs, i32_add, i32_mod, i32_mul, wrap_i32
from genfxn.core.predicates import eval_predicate
from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
    PiecewiseSpec,
)


def _require_int_not_bool(value: int, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be int, got {type(value).__name__}")
    return value


def _eval_linear_i32(a: int, x_term: int, b: int) -> int:
    return i32_add(i32_mul(a, x_term), b)


def _eval_linear(a: int, x_term: int, b: int) -> int:
    return a * x_term + b


def eval_expression(
    expr: Expression,
    x: int,
    *,
    int32_wrap: bool = True,
) -> int:
    x = _require_int_not_bool(x, "x")
    if int32_wrap:
        x = wrap_i32(x)

    match expr:
        case ExprAffine(a=a, b=b):
            if int32_wrap:
                return _eval_linear_i32(a, x, b)
            return _eval_linear(a, x, b)
        case ExprQuadratic(a=a, b=b, c=c):
            if int32_wrap:
                ax = i32_mul(a, x)
                axx = i32_mul(ax, x)
                bx = i32_mul(b, x)
                return i32_add(i32_add(axx, bx), c)
            return a * x * x + b * x + c
        case ExprAbs(a=a, b=b):
            abs_x = i32_abs(x) if int32_wrap else abs(x)
            if int32_wrap:
                return _eval_linear_i32(a, abs_x, b)
            return _eval_linear(a, abs_x, b)
        case ExprMod(divisor=d, a=a, b=b):
            if int32_wrap:
                return _eval_linear_i32(a, i32_mod(x, d), b)
            if d <= 0:
                raise ValueError("divisor must be >= 1")
            return _eval_linear(a, x % d, b)
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def eval_piecewise(
    spec: PiecewiseSpec,
    x: int,
    *,
    int32_wrap: bool = True,
) -> int:
    x = _require_int_not_bool(x, "x")
    if int32_wrap:
        x = wrap_i32(x)

    for branch in spec.branches:
        if eval_predicate(branch.condition, x, int32_wrap=int32_wrap):
            return eval_expression(
                branch.expr,
                x,
                int32_wrap=int32_wrap,
            )
    return eval_expression(
        spec.default_expr,
        x,
        int32_wrap=int32_wrap,
    )
