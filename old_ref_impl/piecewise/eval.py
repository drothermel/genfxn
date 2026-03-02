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


def _eval_linear(a: int, x_term: int, b: int) -> int:
    return a * x_term + b


def eval_expression(expr: Expression, x: int) -> int:
    x = _require_int_not_bool(x, "x")

    match expr:
        case ExprAffine(a=a, b=b):
            return _eval_linear(a, x, b)
        case ExprQuadratic(a=a, b=b, c=c):
            return a * x * x + b * x + c
        case ExprAbs(a=a, b=b):
            return _eval_linear(a, abs(x), b)
        case ExprMod(divisor=d, a=a, b=b):
            if d <= 0:
                raise ValueError("divisor must be >= 1")
            return _eval_linear(a, x % d, b)
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def eval_piecewise(spec: PiecewiseSpec, x: int) -> int:
    x = _require_int_not_bool(x, "x")

    for branch in spec.branches:
        if eval_predicate(branch.condition, x):
            return eval_expression(branch.expr, x)
    return eval_expression(spec.default_expr, x)
