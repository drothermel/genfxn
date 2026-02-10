import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Issue, Severity

intervals_eval = pytest.importorskip("genfxn.intervals.eval")
intervals_models = pytest.importorskip("genfxn.intervals.models")
intervals_task = pytest.importorskip("genfxn.intervals.task")
intervals_validate = pytest.importorskip("genfxn.intervals.validate")

eval_intervals = intervals_eval.eval_intervals
IntervalsAxes = intervals_models.IntervalsAxes
IntervalsSpec = intervals_models.IntervalsSpec
generate_intervals_task = intervals_task.generate_intervals_task

CODE_CODE_EXEC_ERROR = intervals_validate.CODE_CODE_EXEC_ERROR
CODE_CODE_PARSE_ERROR = intervals_validate.CODE_CODE_PARSE_ERROR
CODE_QUERY_INPUT_TYPE = intervals_validate.CODE_QUERY_INPUT_TYPE
CODE_QUERY_OUTPUT_MISMATCH = intervals_validate.CODE_QUERY_OUTPUT_MISMATCH
CODE_QUERY_OUTPUT_TYPE = intervals_validate.CODE_QUERY_OUTPUT_TYPE
CODE_SEMANTIC_MISMATCH = intervals_validate.CODE_SEMANTIC_MISMATCH
CODE_UNSAFE_AST = intervals_validate.CODE_UNSAFE_AST

_validate_intervals_task = intervals_validate.validate_intervals_task


def validate_intervals_task(
    *args: Any, **kwargs: Any
) -> list[Issue]:
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_intervals_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_intervals_task(rng=random.Random(42))


def test_generated_task_has_no_errors(baseline_task: Task) -> None:
    issues = validate_intervals_task(baseline_task)
    errors = [issue for issue in issues if issue.severity == Severity.ERROR]
    assert errors == []


def test_unsafe_ast_is_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(intervals):\n    import os\n    return 0"}
    )
    issues = validate_intervals_task(corrupted)
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
    issues = validate_intervals_task(corrupted)
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
    issues = validate_intervals_task(corrupted)
    assert any(issue.code == CODE_QUERY_OUTPUT_MISMATCH for issue in issues)


def test_semantic_mismatch_detected(baseline_task: Task) -> None:
    spec = IntervalsSpec.model_validate(baseline_task.spec, strict=True)
    expected = eval_intervals(spec, [(0, 0)])
    corrupted = baseline_task.model_copy(
        update={"code": f"def f(intervals):\n    return {expected + 1}"}
    )
    issues = validate_intervals_task(
        corrupted,
        axes=IntervalsAxes(
            n_intervals_range=(1, 1),
            endpoint_range=(0, 0),
            max_span_range=(0, 0),
            allow_reversed_interval_prob_range=(0.0, 0.0),
            degenerate_interval_prob_range=(1.0, 1.0),
            nested_interval_prob_range=(0.0, 0.0),
        ),
        semantic_trials=4,
        max_semantic_issues=4,
        random_seed=123,
    )
    assert any(issue.code == CODE_SEMANTIC_MISMATCH for issue in issues)


def test_execute_untrusted_code_false_skips_exec_errors(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "raise ValueError(1)"}
    )
    issues = _validate_intervals_task(corrupted, execute_untrusted_code=False)
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_execute_untrusted_code_true_reports_exec_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "raise ValueError(1)"}
    )
    issues = _validate_intervals_task(corrupted, execute_untrusted_code=True)
    assert any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_non_string_python_code_payload_reports_parse_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": {"python": 123}}
    )
    issues = validate_intervals_task(corrupted)
    assert any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)
