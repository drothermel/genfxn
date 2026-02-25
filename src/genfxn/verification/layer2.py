from __future__ import annotations

import logging

from genfxn.core.models import Task
from genfxn.verification.adapters import (
    evaluate_input,
    generate_layer2_inputs,
    validate_spec_for_task,
)
from genfxn.verification.models import (
    VerificationCase,
    VerificationLayer,
)

logger = logging.getLogger(__name__)


def generate_layer2_cases(
    task: Task,
    *,
    count: int = 128,
    seed: int = 0,
) -> list[VerificationCase]:
    spec_obj = validate_spec_for_task(task.family, task.spec)

    cases: list[VerificationCase] = []
    attempt = 0
    max_attempts = 16
    while len(cases) < count and attempt < max_attempts:
        remaining = count - len(cases)
        batch_count = max(remaining * 2, 32)
        sampled_inputs = generate_layer2_inputs(
            task.family,
            task_id=task.task_id,
            spec_obj=spec_obj,
            axes=task.axes,
            count=batch_count,
            seed=seed + attempt,
        )
        for input_value in sampled_inputs:
            try:
                expected = evaluate_input(task.family, spec_obj, input_value)
            except Exception as exc:
                logger.debug(
                    "Skipping layer2 input evaluation for task %s at "
                    "sample_index=%d input=%r: %s",
                    task.task_id,
                    len(cases),
                    input_value,
                    exc,
                    exc_info=True,
                )
                continue

            idx = len(cases)
            cases.append(
                VerificationCase(
                    task_id=task.task_id,
                    family=task.family,
                    layer=VerificationLayer.LAYER2_PROPERTY,
                    case_id=f"layer2-{idx:04d}",
                    input=input_value,
                    expected_output=expected,
                    seed=seed + attempt,
                    source_detail={
                        "sample_index": idx,
                        "generator": "domain_aware",
                        "attempt": attempt,
                    },
                )
            )
            if len(cases) >= count:
                break
        attempt += 1

    if len(cases) < count:
        raise ValueError(
            f"Unable to generate {count} valid layer2 cases "
            f"for {task.task_id}; "
            f"built {len(cases)}"
        )
    return cases
