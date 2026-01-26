import random

from genfxn.core.predicates import Predicate, PredicateLe, PredicateLt
from genfxn.piecewise.models import (
    Branch,
    ExprAbs,
    ExprAffine,
    Expression,
    ExprMod,
    ExprQuadratic,
    ExprType,
    PiecewiseAxes,
    PiecewiseSpec,
)


def sample_expression(
    expr_type: ExprType,
    coeff_range: tuple[int, int],
    divisor_range: tuple[int, int],
    rng: random.Random,
) -> Expression:
    lo, hi = coeff_range
    if lo > hi:
        raise ValueError(f"coeff_range: low ({lo}) must be <= high ({hi})")

    if expr_type == ExprType.MOD:
        div_lo, div_hi = divisor_range
        if div_lo > div_hi:
            raise ValueError(f"divisor_range: low ({div_lo}) must be <= high ({div_hi})")
        if div_lo < 1:
            raise ValueError(f"divisor_range: bounds must be >= 1, got ({div_lo}, {div_hi})")

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
            divisor = rng.randint(divisor_range[0], divisor_range[1])
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


def sample_piecewise_spec(
    axes: PiecewiseAxes, rng: random.Random | None = None
) -> PiecewiseSpec:
    if rng is None:
        rng = random.Random()

    n_branches = axes.n_branches
    lo_thresh, hi_thresh = axes.threshold_range

    if lo_thresh > hi_thresh:
        raise ValueError(
            f"threshold_range: low ({lo_thresh}) must be <= high ({hi_thresh})"
        )

    thresholds = sorted(
        rng.sample(
            range(lo_thresh, hi_thresh + 1), min(n_branches, hi_thresh - lo_thresh + 1)
        )
    )

    branches: list[Branch] = []
    for thresh in thresholds:
        expr_type = rng.choice(axes.expr_types)
        expr = sample_expression(expr_type, axes.coeff_range, axes.divisor_range, rng)
        condition = sample_condition(thresh, rng)
        branches.append(Branch(condition=condition, expr=expr))

    default_expr_type = rng.choice(axes.expr_types)
    default_expr = sample_expression(
        default_expr_type, axes.coeff_range, axes.divisor_range, rng
    )

    return PiecewiseSpec(branches=branches, default_expr=default_expr)
