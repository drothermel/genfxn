import random

from genfxn.core.predicates import Predicate, PredicateLe, PredicateLt
from genfxn.piecewise.models import (
    Branch,
    ExprAbs,
    ExprAffine,
    ExprMod,
    ExprQuadratic,
    Expression,
    ExprType,
    PiecewiseAxes,
    PiecewiseSpec,
)


def sample_expression(
    expr_type: ExprType,
    coeff_range: tuple[int, int],
    rng: random.Random,
) -> Expression:
    lo, hi = coeff_range
    match expr_type:
        case ExprType.AFFINE:
            return ExprAffine(
                a=rng.randint(lo, hi),
                b=rng.randint(lo, hi),
            )
        case ExprType.QUADRATIC:
            return ExprQuadratic(
                a=rng.randint(lo, hi),
                b=rng.randint(lo, hi),
                c=rng.randint(lo, hi),
            )
        case ExprType.ABS:
            return ExprAbs(
                a=rng.randint(lo, hi),
                b=rng.randint(lo, hi),
            )
        case ExprType.MOD:
            divisor = rng.randint(2, 10)
            return ExprMod(
                divisor=divisor,
                a=rng.randint(lo, hi),
                b=rng.randint(lo, hi),
            )
        case _:
            raise ValueError(f"Unknown expression type: {expr_type}")


def sample_condition(threshold: int, rng: random.Random) -> Predicate:
    if rng.choice([True, False]):
        return PredicateLt(value=threshold)
    return PredicateLe(value=threshold)


def sample_piecewise_spec(axes: PiecewiseAxes, rng: random.Random | None = None) -> PiecewiseSpec:
    if rng is None:
        rng = random.Random()

    n_branches = axes.n_branches
    lo_thresh, hi_thresh = axes.threshold_range

    thresholds = sorted(rng.sample(range(lo_thresh, hi_thresh + 1), min(n_branches, hi_thresh - lo_thresh + 1)))

    branches: list[Branch] = []
    for thresh in thresholds:
        expr_type = rng.choice(axes.expr_types)
        expr = sample_expression(expr_type, axes.coeff_range, rng)
        condition = sample_condition(thresh, rng)
        branches.append(Branch(condition=condition, expr=expr))

    default_expr_type = rng.choice(axes.expr_types)
    default_expr = sample_expression(default_expr_type, axes.coeff_range, rng)

    return PiecewiseSpec(branches=branches, default_expr=default_expr)
