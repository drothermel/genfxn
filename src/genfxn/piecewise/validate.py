import ast
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.piecewise.eval import eval_piecewise
from genfxn.piecewise.models import PiecewiseAxes, PiecewiseSpec

CODE_TASK_ID_MISMATCH = "TASK_ID_MISMATCH"
CODE_SPEC_DESERIALIZE_ERROR = "SPEC_DESERIALIZE_ERROR"
CODE_CODE_PARSE_ERROR = "CODE_PARSE_ERROR"
CODE_CODE_EXEC_ERROR = "CODE_EXEC_ERROR"
CODE_CODE_MISSING_FUNC = "CODE_MISSING_FUNC"
CODE_CODE_RUNTIME_ERROR = "CODE_RUNTIME_ERROR"
CODE_QUERY_INPUT_TYPE = "QUERY_INPUT_TYPE"
CODE_QUERY_OUTPUT_TYPE = "QUERY_OUTPUT_TYPE"
CODE_QUERY_OUTPUT_MISMATCH = "QUERY_OUTPUT_MISMATCH"
CODE_SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"
CODE_FUNC_NOT_CALLABLE = "FUNC_NOT_CALLABLE"
CURRENT_FAMILY = "piecewise"


def _validate_task_id(task: Task) -> list[Issue]:
    expected = task_id_from_spec(family=task.family, spec=task.spec)
    if task.task_id != expected:
        return [
            Issue(
                code=CODE_TASK_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"task_id '{task.task_id}' does not match spec hash '{expected}'"
                ),
                location="task_id",
                task_id=task.task_id,
            )
        ]
    return []


def _validate_spec_deserialize(task: Task) -> tuple[list[Issue], PiecewiseSpec | None]:
    try:
        spec = PiecewiseSpec.model_validate(task.spec, strict=True)
        return [], spec
    except ValidationError as e:
        return [
            Issue(
                code=CODE_SPEC_DESERIALIZE_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to deserialize spec: {e}",
                location="spec",
                task_id=task.task_id,
            )
        ], None


def _validate_code_compile(
    task: Task,
) -> tuple[list[Issue], Callable[[int], int] | None]:
    try:
        ast.parse(task.code)
    except SyntaxError as e:
        return [
            Issue(
                code=CODE_CODE_PARSE_ERROR,
                severity=Severity.ERROR,
                message=f"Syntax error in code: {e}",
                location="code",
                task_id=task.task_id,
            )
        ], None

    namespace: dict[str, Any] = {}
    try:
        exec(task.code, namespace)  # noqa: S102
    except Exception as e:
        return [
            Issue(
                code=CODE_CODE_EXEC_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to execute code: {e}",
                location="code",
                task_id=task.task_id,
            )
        ], None

    if "f" not in namespace:
        return [
            Issue(
                code=CODE_CODE_MISSING_FUNC,
                severity=Severity.ERROR,
                message="Function 'f' not found in code namespace",
                location="code",
                task_id=task.task_id,
            )
        ], None

    if not callable(namespace["f"]):
        return [
            Issue(
                code=CODE_FUNC_NOT_CALLABLE,
                severity=Severity.ERROR,
                message=f"Function 'f' is not callable: {type(namespace['f'])}",
                location="code.f",
                task_id=task.task_id,
            )
        ], None

    return [], namespace["f"]


def _validate_query_types(task: Task, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, int):
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=severity,
                    message=f"Query input is {type(q.input).__name__}, expected int",
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )
        if not isinstance(q.output, int):
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_TYPE,
                    severity=severity,
                    message=f"Query output is {type(q.output).__name__}, expected int",
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_query_outputs(task: Task, spec: PiecewiseSpec) -> list[Issue]:
    issues: list[Issue] = []

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, int):
            continue
        expected = eval_piecewise(spec, q.input)
        if q.output != expected:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_MISMATCH,
                    severity=Severity.ERROR,
                    message=(
                        f"Query output {q.output} != expected {expected} for input "
                        f"{q.input}"
                    ),
                    location=f"queries[{i}]",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_semantics(
    task: Task,
    func: Callable[[int], int],
    spec: PiecewiseSpec,
    value_range: tuple[int, int],
) -> list[Issue]:
    issues: list[Issue] = []
    lo, hi = value_range

    for x in range(lo, hi + 1):
        try:
            actual = func(x)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=Severity.ERROR,
                    message=f"f({x}) raised {type(e).__name__}: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            )
            continue

        expected = eval_piecewise(spec, x)
        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_SEMANTIC_MISMATCH,
                    severity=Severity.ERROR,
                    message=f"f({x}) = {actual}, expected {expected}",
                    location="code",
                    task_id=task.task_id,
                )
            )

    return issues


def _get_threshold_value(condition: dict[str, Any]) -> int | None:
    kind = condition.get("kind")
    if kind in ("lt", "le", "gt", "ge"):
        return condition.get("value")
    return None


def _check_monotonic_thresholds(task: Task, spec: PiecewiseSpec) -> list[Issue]:
    thresholds: list[int] = []
    for branch in spec.branches:
        cond_dict = branch.condition.model_dump()
        val = _get_threshold_value(cond_dict)
        if val is not None:
            thresholds.append(val)

    if len(thresholds) < 2:
        return []

    is_monotonic = all(
        thresholds[i] < thresholds[i + 1] for i in range(len(thresholds) - 1)
    )
    if not is_monotonic:
        return [
            Issue(
                code=CODE_NON_MONOTONIC_THRESHOLDS,
                severity=Severity.WARNING,
                message=f"Branch thresholds are not strictly increasing: {thresholds}",
                location="spec.branches",
                task_id=task.task_id,
            )
        ]

    return []


def validate_piecewise_task(
    task: Task,
    value_range: tuple[int, int] | None = None,
    strict: bool = True,
) -> list[Issue]:
    if task.family != CURRENT_FAMILY:
        return [
            Issue(
                code=WRONG_FAMILY,
                severity=Severity.ERROR,
                message=f"Task family '{task.family}' is not '{CURRENT_FAMILY}'",
            )
        ]
    if value_range is None:
        value_range = PiecewiseAxes().value_range

    issues: list[Issue] = []

    issues.extend(_validate_task_id(task))

    spec_issues, spec = _validate_spec_deserialize(task)
    issues.extend(spec_issues)

    code_issues, func = _validate_code_compile(task)
    issues.extend(code_issues)

    issues.extend(_validate_query_types(task, strict))

    if spec is not None:
        issues.extend(_validate_query_outputs(task, spec))

    if spec is not None and func is not None:
        issues.extend(_validate_semantics(task, func, spec, value_range))

    if spec is not None:
        issues.extend(_check_monotonic_thresholds(task, spec))

    return issues
