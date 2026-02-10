import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Issue, Severity
from genfxn.temporal_logic.models import TemporalLogicAxes, TemporalLogicSpec
from genfxn.temporal_logic.task import generate_temporal_logic_task
from genfxn.temporal_logic.validate import (
    CODE_AXES_DESERIALIZE_ERROR,
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_UNSAFE_AST,
)
from genfxn.temporal_logic.validate import (
    validate_temporal_logic_task as _validate_temporal_logic_task,
)


def validate_temporal_logic_task(
    *args: Any, **kwargs: Any
) -> list[Issue]:
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_temporal_logic_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    axes = TemporalLogicAxes(
        target_difficulty=3,
        formula_depth_range=(2, 4),
        sequence_length_range=(0, 8),
        value_range=(-6, 6),
        predicate_constant_range=(-5, 5),
    )
    return generate_temporal_logic_task(axes=axes, rng=random.Random(42))


def test_generated_task_has_no_errors(baseline_task: Task) -> None:
    axes = TemporalLogicAxes.model_validate(baseline_task.axes or {})
    issues = validate_temporal_logic_task(
        baseline_task,
        axes=axes,
        semantic_trials=12,
        random_seed=123,
    )
    errors = [issue for issue in issues if issue.severity == Severity.ERROR]
    assert errors == []


def test_unsafe_ast_is_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(xs):\n    import os\n    return 0"}
    )
    issues = validate_temporal_logic_task(corrupted)
    assert any(issue.code == CODE_UNSAFE_AST for issue in issues)


def test_query_input_output_type_mismatch_detected(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(input="bad", output="bad", tag=QueryTag.TYPICAL)
            ]
        }
    )
    issues = validate_temporal_logic_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_TYPE for issue in issues)
    assert any(issue.code == CODE_QUERY_OUTPUT_TYPE for issue in issues)


def test_query_output_mismatch_detected(baseline_task: Task) -> None:
    query = baseline_task.queries[0]
    bad_query = Query(
        input=query.input,
        output=query.output + 1,
        tag=query.tag,
    )
    corrupted = baseline_task.model_copy(update={"queries": [bad_query]})
    issues = validate_temporal_logic_task(corrupted)
    assert any(issue.code == CODE_QUERY_OUTPUT_MISMATCH for issue in issues)


def test_semantic_mismatch_detected(baseline_task: Task) -> None:
    spec = TemporalLogicSpec.model_validate(baseline_task.spec, strict=True)
    expected = _validate_expected(spec, [0, 1, -1])
    corrupted = baseline_task.model_copy(
        update={"code": f"def f(xs):\n    return {expected + 1}"}
    )
    axes = TemporalLogicAxes.model_validate(baseline_task.axes or {})
    issues = validate_temporal_logic_task(
        corrupted,
        axes=axes,
        semantic_trials=6,
        max_semantic_issues=4,
        random_seed=7,
    )
    assert any(issue.code == CODE_SEMANTIC_MISMATCH for issue in issues)


def test_semantic_issue_capping(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(xs):\n    return 1000000000"}
    )
    axes = TemporalLogicAxes.model_validate(baseline_task.axes or {})
    issues = validate_temporal_logic_task(
        corrupted,
        axes=axes,
        execute_untrusted_code=True,
        semantic_trials=20,
        max_semantic_issues=3,
        random_seed=7,
    )
    mismatches = [
        issue for issue in issues if issue.code == CODE_SEMANTIC_MISMATCH
    ]
    capped = [
        issue
        for issue in issues
        if issue.code == CODE_SEMANTIC_ISSUES_CAPPED
    ]
    assert len(mismatches) == 3
    assert len(capped) == 1


def test_execute_untrusted_code_false_skips_exec_errors(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": "raise ValueError(1)"})
    issues = _validate_temporal_logic_task(
        corrupted,
        execute_untrusted_code=False,
    )
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_execute_untrusted_code_true_reports_exec_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": "raise ValueError(1)"})
    issues = _validate_temporal_logic_task(
        corrupted,
        execute_untrusted_code=True,
    )
    assert any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_non_string_python_code_payload_reports_parse_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": {"python": 123}})
    issues = validate_temporal_logic_task(corrupted)
    assert any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)


def test_non_python_code_map_skips_python_validation(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "code": {
                "java": "public static int f(int[] xs) { return 0; }"
            }
        }
    )
    issues = validate_temporal_logic_task(corrupted)
    assert not any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)
    assert not any(issue.code == CODE_CODE_MISSING_FUNC for issue in issues)


def test_exec_function_is_closed_after_validation(
    baseline_task: Task,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    was_closed = False
    call_count = 0

    def fake_fn(xs: list[int]) -> int:
        del xs
        nonlocal call_count
        call_count += 1
        return 0

    def _close() -> None:
        nonlocal was_closed
        was_closed = True

    fake_fn.close = _close  # type: ignore[attr-defined]

    def _stub_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        return {"f": fake_fn}

    monkeypatch.setattr(
        "genfxn.temporal_logic.validate.execute_code_restricted",
        _stub_execute,
    )

    axes = TemporalLogicAxes.model_validate(baseline_task.axes or {})
    validate_temporal_logic_task(
        baseline_task,
        axes=axes,
        execute_untrusted_code=True,
        semantic_trials=1,
        random_seed=123,
    )

    assert call_count >= 1
    assert was_closed is True


def test_bool_query_values_are_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(input=[True, 1], output=False, tag=QueryTag.TYPICAL)
            ]
        }
    )
    issues = validate_temporal_logic_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_TYPE for issue in issues)
    assert any(issue.code == CODE_QUERY_OUTPUT_TYPE for issue in issues)


def test_validator_uses_task_axes_when_axes_not_passed(
    baseline_task: Task,
) -> None:
    spec = TemporalLogicSpec.model_validate(baseline_task.spec, strict=True)
    expected_empty = _validate_expected(spec, [])
    corrupted = baseline_task.model_copy(
        update={
            "axes": {
                "sequence_length_range": [0, 0],
                "value_range": [0, 0],
            },
            "code": (
                "def f(xs):\n"
                "    if len(xs) == 0:\n"
                f"        return {expected_empty}\n"
                "    return 10_000\n"
            ),
        }
    )
    issues = validate_temporal_logic_task(
        corrupted,
        axes=None,
        semantic_trials=6,
        random_seed=5,
    )
    assert not any(issue.code == CODE_SEMANTIC_MISMATCH for issue in issues)


def test_invalid_task_axes_emit_structured_issue(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"axes": {"formula_depth_range": [0, 100]}}
    )
    issues = validate_temporal_logic_task(corrupted, axes=None, strict=False)
    assert any(issue.code == CODE_AXES_DESERIALIZE_ERROR for issue in issues)


def _validate_expected(spec: TemporalLogicSpec, xs: list[int]) -> int:
    from genfxn.temporal_logic.eval import eval_temporal_logic

    return eval_temporal_logic(spec, xs)
