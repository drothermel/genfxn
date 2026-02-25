import random

from genfxn.core.family_registry import FAMILY_ORDER, generate_task_for_family
from genfxn.verification.adapters import (
    evaluate_input,
    generate_layer2_inputs,
    get_adapter,
    get_registered_families,
    validate_spec_for_task,
)


def test_adapter_registry_covers_all_supported_families() -> None:
    assert get_registered_families() == tuple(FAMILY_ORDER)


def test_all_family_adapters_validate_build_inputs_and_evaluate() -> None:
    for family in FAMILY_ORDER:
        task = generate_task_for_family(
            family, rng=random.Random(17), axes=None
        )
        spec_obj = validate_spec_for_task(family, task.spec)

        adapter = get_adapter(family)
        strategy = adapter.layer2_strategy(
            task_id=task.task_id,
            spec_obj=spec_obj,
            axes=task.axes,
            seed=7,
        )
        assert strategy is not None

        inputs = generate_layer2_inputs(
            family,
            task_id=task.task_id,
            spec_obj=spec_obj,
            axes=task.axes,
            count=8,
            seed=7,
        )
        assert len(inputs) == 8

        for input_value in inputs:
            _ = evaluate_input(family, spec_obj, input_value)
