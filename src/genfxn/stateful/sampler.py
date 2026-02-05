import random

from genfxn.core.predicates import (
    Predicate,
    PredicateAnd,
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateNot,
    PredicateOdd,
    PredicateOr,
    PredicateType,
    render_predicate,
)
from genfxn.core.trace import TraceStep
from genfxn.core.transforms import (
    Transform,
    TransformAbs,
    TransformIdentity,
    TransformNegate,
    TransformPipeline,
    TransformScale,
    TransformShift,
    TransformType,
    render_transform,
)
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulAxes,
    StatefulSpec,
    TemplateType,
    ToggleSumSpec,
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
        case PredicateType.NOT:
            atom_types = [
                PredicateType.EVEN,
                PredicateType.ODD,
                PredicateType.LT,
                PredicateType.LE,
                PredicateType.GT,
                PredicateType.GE,
                PredicateType.MOD_EQ,
            ]
            operand = sample_predicate(
                rng.choice(atom_types), threshold_range, divisor_range, rng
            )
            return PredicateNot(operand=operand)
        case PredicateType.AND:
            atom_types = [
                PredicateType.EVEN,
                PredicateType.ODD,
                PredicateType.LT,
                PredicateType.LE,
                PredicateType.GT,
                PredicateType.GE,
                PredicateType.MOD_EQ,
            ]
            n = rng.choice([2, 3])
            operands = [
                sample_predicate(
                    rng.choice(atom_types), threshold_range, divisor_range, rng
                )
                for _ in range(n)
            ]
            return PredicateAnd(operands=operands)
        case PredicateType.OR:
            atom_types = [
                PredicateType.EVEN,
                PredicateType.ODD,
                PredicateType.LT,
                PredicateType.LE,
                PredicateType.GT,
                PredicateType.GE,
                PredicateType.MOD_EQ,
            ]
            n = rng.choice([2, 3])
            operands = [
                sample_predicate(
                    rng.choice(atom_types), threshold_range, divisor_range, rng
                )
                for _ in range(n)
            ]
            return PredicateOr(operands=operands)
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
        case TransformType.PIPELINE:
            n = rng.choice([2, 3])
            param_types = [TransformType.SHIFT, TransformType.SCALE]
            nonparam_types = [TransformType.ABS, TransformType.NEGATE]
            # Ensure at least one param step for meaningful pipelines
            first = sample_transform(
                rng.choice(param_types), shift_range, scale_range, rng
            )
            rest_types = param_types + nonparam_types
            rest = [
                sample_transform(
                    rng.choice(rest_types), shift_range, scale_range, rng
                )
                for _ in range(n - 1)
            ]
            steps = [first] + rest
            return TransformPipeline(steps=steps)
        case _:
            raise ValueError(f"Unknown transform type: {trans_type}")


def sample_stateful_spec(
    axes: StatefulAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> StatefulSpec:
    if rng is None:
        rng = random.Random()

    template = rng.choice(axes.templates)

    if trace is not None:
        trace.append(
            TraceStep(
                step="sample_template",
                choice=f"Selected template: {template.value}",
                value=template.value,
            )
        )

    match template:
        case TemplateType.CONDITIONAL_LINEAR_SUM:
            pred_type = rng.choice(axes.predicate_types)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_predicate_type",
                        choice=f"Predicate type: {pred_type.value}",
                        value=pred_type.value,
                    )
                )

            predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_predicate",
                        choice=f"Predicate: {render_predicate(predicate)}",
                        value=predicate.model_dump(),
                    )
                )

            true_trans_type = rng.choice(axes.transform_types)
            true_transform = sample_transform(
                true_trans_type, axes.shift_range, axes.scale_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_true_transform",
                        choice=f"True: {render_transform(true_transform)}",
                        value=true_transform.model_dump(),
                    )
                )

            false_trans_type = rng.choice(axes.transform_types)
            false_transform = sample_transform(
                false_trans_type, axes.shift_range, axes.scale_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_false_transform",
                        choice=f"False: {render_transform(false_transform)}",
                        value=false_transform.model_dump(),
                    )
                )

            init_value = rng.randint(-10, 10)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_init_value",
                        choice=f"Initial value: {init_value}",
                        value=init_value,
                    )
                )

            return ConditionalLinearSumSpec(
                predicate=predicate,
                true_transform=true_transform,
                false_transform=false_transform,
                init_value=init_value,
            )

        case TemplateType.RESETTING_BEST_PREFIX_SUM:
            pred_type = rng.choice(axes.predicate_types)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_predicate_type",
                        choice=f"Reset predicate type: {pred_type.value}",
                        value=pred_type.value,
                    )
                )

            reset_predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_reset_predicate",
                        choice=f"Reset: {render_predicate(reset_predicate)}",
                        value=reset_predicate.model_dump(),
                    )
                )

            init_value = rng.randint(-10, 10)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_init_value",
                        choice=f"Initial value: {init_value}",
                        value=init_value,
                    )
                )

            value_transform = None
            trans_type = rng.choice(axes.transform_types)
            if trans_type != TransformType.IDENTITY:
                value_transform = sample_transform(
                    trans_type, axes.shift_range, axes.scale_range, rng
                )
                if trace is not None:
                    vt_str = render_transform(value_transform)
                    trace.append(
                        TraceStep(
                            step="sample_value_transform",
                            choice=f"Value: {vt_str}",
                            value=value_transform.model_dump(),
                        )
                    )

            return ResettingBestPrefixSumSpec(
                reset_predicate=reset_predicate,
                init_value=init_value,
                value_transform=value_transform,
            )

        case TemplateType.LONGEST_RUN:
            pred_type = rng.choice(axes.predicate_types)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_predicate_type",
                        choice=f"Match predicate type: {pred_type.value}",
                        value=pred_type.value,
                    )
                )

            match_predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_match_predicate",
                        choice=f"Match: {render_predicate(match_predicate)}",
                        value=match_predicate.model_dump(),
                    )
                )

            return LongestRunSpec(match_predicate=match_predicate)

        case TemplateType.TOGGLE_SUM:
            pred_type = rng.choice(axes.predicate_types)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_predicate_type",
                        choice=f"Toggle predicate type: {pred_type.value}",
                        value=pred_type.value,
                    )
                )

            toggle_predicate = sample_predicate(
                pred_type, axes.threshold_range, axes.divisor_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_toggle_predicate",
                        choice=f"Toggle: {render_predicate(toggle_predicate)}",
                        value=toggle_predicate.model_dump(),
                    )
                )

            on_trans_type = rng.choice(axes.transform_types)
            on_transform = sample_transform(
                on_trans_type, axes.shift_range, axes.scale_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_on_transform",
                        choice=f"On: {render_transform(on_transform)}",
                        value=on_transform.model_dump(),
                    )
                )

            off_trans_type = rng.choice(axes.transform_types)
            off_transform = sample_transform(
                off_trans_type, axes.shift_range, axes.scale_range, rng
            )
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_off_transform",
                        choice=f"Off: {render_transform(off_transform)}",
                        value=off_transform.model_dump(),
                    )
                )

            init_value = rng.randint(-10, 10)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_init_value",
                        choice=f"Initial value: {init_value}",
                        value=init_value,
                    )
                )

            return ToggleSumSpec(
                toggle_predicate=toggle_predicate,
                on_transform=on_transform,
                off_transform=off_transform,
                init_value=init_value,
            )

        case _:
            raise ValueError(f"Unknown template: {template}")
