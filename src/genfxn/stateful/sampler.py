import random

from genfxn.core.predicates import (
    Predicate,
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
)
from genfxn.core.transforms import (
    Transform,
    TransformAbs,
    TransformIdentity,
    TransformNegate,
    TransformScale,
    TransformShift,
)
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    PredicateType,
    ResettingBestPrefixSumSpec,
    StatefulAxes,
    StatefulSpec,
    TemplateType,
    TransformType,
)


def sample_predicate(
    pred_type: PredicateType,
    threshold_range: tuple[int, int],
    divisor_range: tuple[int, int],
    rng: random.Random,
) -> Predicate:
    match pred_type:
        case PredicateType.EVEN:
            return PredicateEven()
        case PredicateType.ODD:
            return PredicateOdd()
        case PredicateType.LT:
            return PredicateLt(value=rng.randint(*threshold_range))
        case PredicateType.LE:
            return PredicateLe(value=rng.randint(*threshold_range))
        case PredicateType.GT:
            return PredicateGt(value=rng.randint(*threshold_range))
        case PredicateType.GE:
            return PredicateGe(value=rng.randint(*threshold_range))
        case PredicateType.MOD_EQ:
            divisor = rng.randint(*divisor_range)
            remainder = rng.randint(0, divisor - 1)
            return PredicateModEq(divisor=divisor, remainder=remainder)
        case _:
            raise ValueError(f"Unknown predicate type: {pred_type}")


def sample_transform(
    trans_type: TransformType,
    shift_range: tuple[int, int],
    scale_range: tuple[int, int],
    rng: random.Random,
) -> Transform:
    match trans_type:
        case TransformType.IDENTITY:
            return TransformIdentity()
        case TransformType.ABS:
            return TransformAbs()
        case TransformType.SHIFT:
            return TransformShift(offset=rng.randint(*shift_range))
        case TransformType.NEGATE:
            return TransformNegate()
        case TransformType.SCALE:
            return TransformScale(factor=rng.randint(*scale_range))
        case _:
            raise ValueError(f"Unknown transform type: {trans_type}")


def sample_stateful_spec(
    axes: StatefulAxes, rng: random.Random | None = None
) -> StatefulSpec:
    if rng is None:
        rng = random.Random()

    template = rng.choice(axes.templates)

    match template:
        case TemplateType.CONDITIONAL_LINEAR_SUM:
            pred_type = rng.choice(axes.predicate_types)
            predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            true_trans_type = rng.choice(axes.transform_types)
            true_transform = sample_transform(
                true_trans_type, axes.shift_range, axes.scale_range, rng
            )
            false_trans_type = rng.choice(axes.transform_types)
            false_transform = sample_transform(
                false_trans_type, axes.shift_range, axes.scale_range, rng
            )
            init_value = rng.randint(-10, 10)
            return ConditionalLinearSumSpec(
                predicate=predicate,
                true_transform=true_transform,
                false_transform=false_transform,
                init_value=init_value,
            )

        case TemplateType.RESETTING_BEST_PREFIX_SUM:
            pred_type = rng.choice(axes.predicate_types)
            reset_predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            init_value = rng.randint(-10, 10)
            return ResettingBestPrefixSumSpec(
                reset_predicate=reset_predicate,
                init_value=init_value,
            )

        case TemplateType.LONGEST_RUN:
            pred_type = rng.choice(axes.predicate_types)
            match_predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            return LongestRunSpec(match_predicate=match_predicate)

        case _:
            raise ValueError(f"Unknown template: {template}")
