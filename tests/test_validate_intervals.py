import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Issue, Severity
from genfxn.intervals.eval import eval_intervals
from genfxn.intervals.models import IntervalsAxes, IntervalsSpec
from genfxn.intervals.task import generate_intervals_task
from genfxn.intervals.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_QUERY_INPUT_DUPLICATE,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_UNSAFE_AST,
)
from genfxn.intervals.validate import (
    validate_intervals_task as _validate_intervals_task,
)


def validate_intervals_task(*args: Any, **kwargs: Any) -> list[Issue]:
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
            "queries": [Query(input="bad", output="bad", tag=QueryTag.TYPICAL)]
        }
    )
    issues = validate_intervals_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_TYPE for issue in issues)
    assert any(issue.code == CODE_QUERY_OUTPUT_TYPE for issue in issues)


def test_bool_query_values_are_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(
                    input=[(True, 1)],
                    output=False,
                    tag=QueryTag.TYPICAL,
                )
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


def test_duplicate_query_input_within_tag_is_rejected(
    baseline_task: Task,
) -> None:
    query = baseline_task.queries[0]
    duplicate = Query(
        input=query.input,
        output=query.output,
        tag=query.tag,
    )
    corrupted = baseline_task.model_copy(update={"queries": [query, duplicate]})
    issues = validate_intervals_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_DUPLICATE for issue in issues)


def test_duplicate_query_input_across_tags_is_allowed(
    baseline_task: Task,
) -> None:
    query = baseline_task.queries[0]
    alternate_tag = (
        QueryTag.BOUNDARY
        if query.tag != QueryTag.BOUNDARY
        else QueryTag.COVERAGE
    )
    duplicate = Query(
        input=query.input,
        output=query.output,
        tag=alternate_tag,
    )
    corrupted = baseline_task.model_copy(update={"queries": [query, duplicate]})
    issues = validate_intervals_task(corrupted)
    assert not any(issue.code == CODE_QUERY_INPUT_DUPLICATE for issue in issues)


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


def test_semantic_mismatch_issue_capping(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(intervals):\n    return None"}
    )
    issues = validate_intervals_task(
        corrupted,
        execute_untrusted_code=True,
        semantic_trials=20,
        max_semantic_issues=3,
        random_seed=123,
    )
    mismatches = [i for i in issues if i.code == CODE_SEMANTIC_MISMATCH]
    capped = [i for i in issues if i.code == CODE_SEMANTIC_ISSUES_CAPPED]
    assert len(mismatches) == 3
    assert len(capped) == 1


def test_execute_untrusted_code_false_skips_exec_errors(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": "raise ValueError(1)"})
    issues = _validate_intervals_task(corrupted, execute_untrusted_code=False)
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_execute_untrusted_code_true_reports_exec_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(intervals=len(1)):\n    return 0"}
    )
    issues = _validate_intervals_task(corrupted, execute_untrusted_code=True)
    assert any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_non_string_python_code_payload_reports_parse_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": {"python": 123}})
    issues = validate_intervals_task(corrupted)
    assert any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)


def test_non_python_code_map_skips_python_validation(
    baseline_task: Task,
) -> None:
    java_only = baseline_task.model_copy(
        update={
            "code": {"java": "public class Solution {}"},
        }
    )
    issues = validate_intervals_task(java_only)
    blocked_codes = {
        CODE_CODE_PARSE_ERROR,
        CODE_CODE_EXEC_ERROR,
        CODE_CODE_MISSING_FUNC,
    }
    assert not any(issue.code in blocked_codes for issue in issues)


def test_exec_function_is_closed_after_validation(
    baseline_task: Task,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"closed": False, "calls": 0}

    def fake_fn(*args: Any, **kwargs: Any) -> int:
        state["calls"] += 1
        return 0

    def _close() -> None:
        state["closed"] = True

    setattr(fake_fn, "close", _close)

    def _fake_exec(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"f": fake_fn}

    monkeypatch.setattr(
        "genfxn.intervals.validate.execute_code_restricted",
        _fake_exec,
    )

    _validate_intervals_task(
        baseline_task,
        execute_untrusted_code=True,
        semantic_trials=1,
        random_seed=123,
    )

    assert state["calls"] >= 1
    assert state["closed"] is True
