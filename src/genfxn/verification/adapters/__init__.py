from __future__ import annotations

from typing import Any

from genfxn.verification.adapters.base import (
    Layer3Mode,
    Layer3MutantCandidate,
)
from genfxn.verification.adapters.common import (
    sample_strategy_examples,
    seed_for_task_layer,
)
from genfxn.verification.adapters.registry import (
    get_adapter,
    get_registered_families,
)


def generate_layer2_inputs(
    family: str,
    *,
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    count: int,
    seed: int = 0,
) -> list[Any]:
    if count <= 0:
        return []

    adapter = get_adapter(family)
    inputs: list[Any] = []

    max_attempts = 8
    for attempt in range(max_attempts):
        remaining = count - len(inputs)
        if remaining <= 0:
            break

        strategy = adapter.layer2_strategy(
            task_id=task_id,
            spec_obj=spec_obj,
            axes=axes,
            seed=seed + attempt,
        )
        attempt_seed = seed_for_task_layer(
            task_id,
            "layer2-draw",
            seed + attempt,
            family=family,
        )
        draws = sample_strategy_examples(
            strategy,
            seed_value=attempt_seed,
            max_examples=max(remaining * 4, 32),
        )
        inputs.extend(draws)
        if len(inputs) >= count:
            break

    return inputs[:count]


def validate_spec_for_task(family: str, spec: Any) -> Any:
    return get_adapter(family).validate_spec(spec)


def evaluate_input(family: str, spec_obj: Any, input_value: Any) -> Any:
    return get_adapter(family).evaluate(spec_obj, input_value)


def generate_layer3_mutants(
    family: str,
    *,
    task_id: str,
    spec_obj: Any,
    spec_dict: dict[str, Any],
    budget: int,
    seed: int,
    mode: Layer3Mode,
) -> list[Layer3MutantCandidate]:
    return get_adapter(family).layer3_mutants(
        task_id=task_id,
        spec_obj=spec_obj,
        spec_dict=spec_dict,
        budget=budget,
        seed=seed,
        mode=mode,
    )


__all__ = [
    "evaluate_input",
    "generate_layer2_inputs",
    "generate_layer3_mutants",
    "get_adapter",
    "get_registered_families",
    "validate_spec_for_task",
]
