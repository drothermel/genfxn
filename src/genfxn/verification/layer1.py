from __future__ import annotations

from genfxn.core.models import Query, Task
from genfxn.verification.models import VerificationCase, VerificationLayer


def generate_layer1_cases(task: Task) -> list[VerificationCase]:
    cases: list[VerificationCase] = []
    for idx, query in enumerate(task.queries):
        if not isinstance(query, Query):
            raise TypeError(
                "task.queries entries must be Query; "
                f"got {type(query).__name__}"
            )
        cases.append(
            VerificationCase(
                task_id=task.task_id,
                family=task.family,
                layer=VerificationLayer.LAYER1_SPEC_BOUNDARY,
                case_id=f"layer1-{idx:04d}",
                input=query.input,
                expected_output=query.output,
                source_detail={"tag": query.tag.value},
            )
        )
    return cases
