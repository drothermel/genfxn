from genfxn.core.predicates import eval_predicate
from genfxn.piecewise.models import (
    Branch,
    ExprAbs,
    ExprAffine,
    ExprMod,
    ExprQuadratic,
    Expression,
    PiecewiseSpec,
)


def eval_expression(expr: Expression, x: int) -> int:
    match expr:
        case ExprAffine(a=a, b=b):
            return a * x + b
        case ExprQuadratic(a=a, b=b, c=c):
            return a * x * x + b * x + c
        case ExprAbs(a=a, b=b):
            return a * abs(x) + b
        case ExprMod(divisor=d, a=a, b=b):
            return a * (x % d) + b
        case _:
            raise ValueError(f"Unknown expression: {expr}")


def eval_piecewise(spec: PiecewiseSpec, x: int) -> int:
    for branch in spec.branches:
        if eval_predicate(branch.condition, x):
            return eval_expression(branch.expr, x)
    return eval_expression(spec.default_expr, x)
