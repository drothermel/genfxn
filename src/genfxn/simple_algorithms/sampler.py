import random

from genfxn.core.predicates import Predicate
from genfxn.core.trace import TraceStep, trace_step
from genfxn.core.transforms import Transform
from genfxn.simple_algorithms.models import (
    PREPROCESS_SCALE_RANGE,
    PREPROCESS_SHIFT_RANGE,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
    TemplateType,
)
from genfxn.stateful.sampler import sample_predicate, sample_transform


def _sample_preprocess(
    axes: SimpleAlgorithmsAxes, rng: random.Random
) -> tuple[Predicate | None, Transform | None]:
    pre_filter = None
    if axes.pre_filter_types is not None:
        pred_type = rng.choice(axes.pre_filter_types)
        pre_filter = sample_predicate(
            pred_type,
            threshold_range=(-50, 50),
            divisor_range=(2, 10),
            rng=rng,
        )

    pre_transform = None
    if axes.pre_transform_types is not None:
        trans_type = rng.choice(axes.pre_transform_types)
        pre_transform = sample_transform(
            trans_type,
            shift_range=PREPROCESS_SHIFT_RANGE,
            scale_range=PREPROCESS_SCALE_RANGE,
            rng=rng,
        )

    return pre_filter, pre_transform


def sample_simple_algorithms_spec(
    axes: SimpleAlgorithmsAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> SimpleAlgorithmsSpec:
    if rng is None:
        rng = random.Random()

    template = rng.choice(axes.templates)
    trace_step(
        trace,
        "sample_template",
        f"Selected template: {template.value}",
        template.value,
    )

    pre_filter, pre_transform = _sample_preprocess(axes, rng)

    match template:
        case TemplateType.MOST_FREQUENT:
            tie_break = rng.choice(axes.tie_break_modes)
            trace_step(
                trace,
                "sample_tie_break",
                f"Tie break mode: {tie_break.value}",
                tie_break.value,
            )

            empty_default = rng.randint(*axes.empty_default_range)
            trace_step(
                trace,
                "sample_empty_default",
                f"Empty default: {empty_default}",
                empty_default,
            )

            tie_default = None
            if axes.tie_default_range is not None:
                tie_default = rng.randint(*axes.tie_default_range)

            return MostFrequentSpec(
                tie_break=tie_break,
                empty_default=empty_default,
                pre_filter=pre_filter,
                pre_transform=pre_transform,
                tie_default=tie_default,
            )

        case TemplateType.COUNT_PAIRS_SUM:
            target = rng.randint(*axes.target_range)
            trace_step(trace, "sample_target", f"Target sum: {target}", target)

            counting_mode = rng.choice(axes.counting_modes)
            trace_step(
                trace,
                "sample_counting_mode",
                f"Counting mode: {counting_mode.value}",
                counting_mode.value,
            )

            no_result_default = None
            if axes.no_result_default_range is not None:
                no_result_default = rng.randint(*axes.no_result_default_range)

            short_list_default = None
            if axes.short_list_default_range is not None:
                short_list_default = rng.randint(*axes.short_list_default_range)

            return CountPairsSumSpec(
                target=target,
                counting_mode=counting_mode,
                pre_filter=pre_filter,
                pre_transform=pre_transform,
                no_result_default=no_result_default,
                short_list_default=short_list_default,
            )

        case TemplateType.MAX_WINDOW_SUM:
            k = rng.randint(*axes.window_size_range)
            trace_step(trace, "sample_window_size", f"Window size k: {k}", k)

            invalid_k_default = rng.randint(*axes.empty_default_range)
            trace_step(
                trace,
                "sample_invalid_k_default",
                f"Invalid k default: {invalid_k_default}",
                invalid_k_default,
            )

            empty_default = None
            if axes.empty_default_for_empty_range is not None:
                empty_default = rng.randint(*axes.empty_default_for_empty_range)

            return MaxWindowSumSpec(
                k=k,
                invalid_k_default=invalid_k_default,
                pre_filter=pre_filter,
                pre_transform=pre_transform,
                empty_default=empty_default,
            )

        case _:
            raise ValueError(f"Unknown template: {template}")
