import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Severity
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.sequence_dp.models import SequenceDpAxes, SequenceDpSpec
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.sequence_dp.validate import (
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
from genfxn.sequence_dp.validate import (
    validate_sequence_dp_task as _validate_sequence_dp_task,
)


def validate_sequence_dp_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_sequence_dp_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_sequence_dp_task(rng=random.Random(42))


def test_generated_task_has_no_errors(baseline_task: Task) -> None:
    issues = validate_sequence_dp_task(baseline_task)
    errors = [issue for issue in issues if issue.severity == Severity.ERROR]
    assert errors == []


def test_unsafe_ast_is_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(a, b):\n    import os\n    return 0"}
    )
    issues = validate_sequence_dp_task(corrupted)
    assert any(issue.code == CODE_UNSAFE_AST for issue in issues)


def test_query_input_output_type_mismatch_detected(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(
                    input={"a": [1], "b": "bad"},
                    output="bad",
                    tag=QueryTag.TYPICAL,
                )
            ]
        }
    )
    issues = validate_sequence_dp_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_TYPE for issue in issues)
    assert any(issue.code == CODE_QUERY_OUTPUT_TYPE for issue in issues)


def test_bool_query_values_are_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(
                    input={"a": [True, 1], "b": [0]},
                    output=False,
                    tag=QueryTag.TYPICAL,
                )
            ]
        }
    )
    issues = validate_sequence_dp_task(corrupted)
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
    issues = validate_sequence_dp_task(corrupted)
    assert any(issue.code == CODE_QUERY_OUTPUT_MISMATCH for issue in issues)


def test_semantic_mismatch_detected(baseline_task: Task) -> None:
    spec = SequenceDpSpec.model_validate(baseline_task.spec, strict=True)
    expected = eval_sequence_dp(spec, [0], [0])
    corrupted = baseline_task.model_copy(
        update={"code": f"def f(a, b):\n    return {expected + 1}"}
    )
    issues = validate_sequence_dp_task(
        corrupted,
        axes=SequenceDpAxes(
            len_a_range=(1, 1),
            len_b_range=(1, 1),
            value_range=(0, 0),
        ),
        semantic_trials=4,
        max_semantic_issues=4,
        random_seed=123,
    )
    assert any(issue.code == CODE_SEMANTIC_MISMATCH for issue in issues)


def test_semantic_mismatch_issue_capping(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(a, b):\n    return None"}
    )
    issues = validate_sequence_dp_task(
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
    corrupted = baseline_task.model_copy(
        update={"code": "raise RuntimeError(1)"}
    )
    issues = _validate_sequence_dp_task(corrupted, execute_untrusted_code=False)
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_execute_untrusted_code_true_reports_exec_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(a, b=len(1)):\n    return 0"}
    )
    issues = _validate_sequence_dp_task(corrupted, execute_untrusted_code=True)
    assert any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_non_string_python_code_payload_reports_parse_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": {"python": 123}})
    issues = validate_sequence_dp_task(corrupted)
    assert any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)


def test_non_python_code_map_skips_python_validation(
    baseline_task: Task,
) -> None:
    java_only = baseline_task.model_copy(
        update={
            "code": {"java": "public class Solution {}"},
        }
    )
    issues = validate_sequence_dp_task(java_only)
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
        "genfxn.sequence_dp.validate.execute_code_restricted",
        _fake_exec,
    )

    _validate_sequence_dp_task(
        baseline_task,
        execute_untrusted_code=True,
        semantic_trials=1,
        random_seed=123,
    )

    assert state["calls"] >= 1
    assert state["closed"] is True
