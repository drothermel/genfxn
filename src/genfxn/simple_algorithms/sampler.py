import random

from genfxn.core.trace import TraceStep
from genfxn.simple_algorithms.models import (
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
    TemplateType,
)


def sample_simple_algorithms_spec(
    axes: SimpleAlgorithmsAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> SimpleAlgorithmsSpec:
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
        case TemplateType.MOST_FREQUENT:
            tie_break = rng.choice(axes.tie_break_modes)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_tie_break",
                        choice=f"Tie break mode: {tie_break.value}",
                        value=tie_break.value,
                    )
                )

            empty_default = rng.randint(*axes.empty_default_range)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_empty_default",
                        choice=f"Empty default: {empty_default}",
                        value=empty_default,
                    )
                )

            return MostFrequentSpec(
                tie_break=tie_break,
                empty_default=empty_default,
            )

        case TemplateType.COUNT_PAIRS_SUM:
            target = rng.randint(*axes.target_range)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_target",
                        choice=f"Target sum: {target}",
                        value=target,
                    )
                )

            counting_mode = rng.choice(axes.counting_modes)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_counting_mode",
                        choice=f"Counting mode: {counting_mode.value}",
                        value=counting_mode.value,
                    )
                )

            return CountPairsSumSpec(
                target=target,
                counting_mode=counting_mode,
            )

        case TemplateType.MAX_WINDOW_SUM:
            k = rng.randint(*axes.window_size_range)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_window_size",
                        choice=f"Window size k: {k}",
                        value=k,
                    )
                )

            invalid_k_default = rng.randint(*axes.empty_default_range)
            if trace is not None:
                trace.append(
                    TraceStep(
                        step="sample_invalid_k_default",
                        choice=f"Invalid k default: {invalid_k_default}",
                        value=invalid_k_default,
                    )
                )

            return MaxWindowSumSpec(
                k=k,
                invalid_k_default=invalid_k_default,
            )

        case _:
            raise ValueError(f"Unknown template: {template}")
