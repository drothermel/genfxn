from genfxn.core.int32 import i32_abs, i32_add, i32_mul, wrap_i32
from genfxn.core.predicates import eval_predicate
from genfxn.piecewise.models import (
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
    PiecewiseSpec,
)


def _eval_linear_i32(a: int, x_term: int, b: int) -> int:
    return i32_add(i32_mul(a, x_term), b)


def eval_expression(expr: Expression, x: int) -> int:
    x = wrap_i32(x)

    match expr:
        case ExprAffine(a=a, b=b):
            return _eval_linear_i32(a, x, b)
        case ExprQuadratic(a=a, b=b, c=c):
            ax = i32_mul(a, x)
            axx = i32_mul(ax, x)
            bx = i32_mul(b, x)
            return i32_add(i32_add(axx, bx), c)
        case ExprAbs(a=a, b=b):
            return _eval_linear_i32(a, i32_abs(x), b)
        case ExprMod(divisor=d, a=a, b=b):
            return _eval_linear_i32(a, x % d, b)
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def eval_piecewise(spec: PiecewiseSpec, x: int) -> int:
    x = wrap_i32(x)

    for branch in spec.branches:
        if eval_predicate(branch.condition, x):
            return eval_expression(branch.expr, x)
    return eval_expression(spec.default_expr, x)
