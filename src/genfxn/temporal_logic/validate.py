from pydantic import TypeAdapter, ValidationError

from genfxn.core.models import Task
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.temporal_logic.eval import eval_temporal_logic
from genfxn.temporal_logic.models import TemporalLogicSpec

CODE_SPEC_DESERIALIZE_ERROR = "SPEC_DESERIALIZE_ERROR"
CODE_QUERY_INPUT_TYPE = "QUERY_INPUT_TYPE"
CODE_QUERY_OUTPUT_MISMATCH = "QUERY_OUTPUT_MISMATCH"
CURRENT_FAMILY = "temporal_logic"

_spec_adapter = TypeAdapter(TemporalLogicSpec)


def validate_temporal_logic_task(
    task: Task, execute_untrusted_code: bool = True
) -> list[Issue]:
    _ = execute_untrusted_code
    if task.family != CURRENT_FAMILY:
        return [
            Issue(
                code=WRONG_FAMILY,
                severity=Severity.ERROR,
                message=f"Expected family '{CURRENT_FAMILY}'",
                location="family",
                task_id=task.task_id,
            )
        ]

    try:
        spec = _spec_adapter.validate_python(task.spec, strict=True)
    except ValidationError as exc:
        return [
            Issue(
                code=CODE_SPEC_DESERIALIZE_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to deserialize spec: {exc}",
                location="spec",
                task_id=task.task_id,
            )
        ]

    issues: list[Issue] = []
    for idx, query in enumerate(task.queries):
        if not isinstance(query.input, list) or not all(
            isinstance(value, int) for value in query.input
        ):
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=Severity.ERROR,
                    message="Query input must be list[int]",
                    location=f"queries[{idx}].input",
                    task_id=task.task_id,
                )
            )
            continue

        expected = eval_temporal_logic(spec, query.input)
        if query.output != expected:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_MISMATCH,
                    severity=Severity.ERROR,
                    message=(
                        f"Query output mismatch: expected {expected}, got "
                        f"{query.output}"
                    ),
                    location=f"queries[{idx}].output",
                    task_id=task.task_id,
                )
            )

    return issues
