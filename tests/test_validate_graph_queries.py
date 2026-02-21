import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Issue, Severity
from genfxn.graph_queries.eval import eval_graph_queries
from genfxn.graph_queries.models import GraphQueriesAxes, GraphQueriesSpec
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.graph_queries.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_QUERY_INPUT_BOUNDS,
    CODE_QUERY_INPUT_DUPLICATE,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_TASK_ID_MISMATCH,
    CODE_UNSAFE_AST,
)
from genfxn.graph_queries.validate import (
    validate_graph_queries_task as _validate_graph_queries_task,
)


def validate_graph_queries_task(*args: Any, **kwargs: Any) -> list[Issue]:
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_graph_queries_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_graph_queries_task(rng=random.Random(42))


def test_generated_task_has_no_errors(baseline_task: Task) -> None:
    issues = validate_graph_queries_task(baseline_task)
    errors = [issue for issue in issues if issue.severity == Severity.ERROR]
    assert errors == []


def test_unsafe_ast_is_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(src, dst):\n    import os\n    return 0"}
    )
    issues = validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_UNSAFE_AST for issue in issues)


def test_stale_wrap_helper_call_is_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(src, dst):\n    return _wrap_i64(src + dst)"}
    )
    issues = validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_UNSAFE_AST for issue in issues)


def test_type_call_is_rejected_by_ast_whitelist(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(src, dst):\n    return type(src)"}
    )
    issues = validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_UNSAFE_AST for issue in issues)


def test_query_input_output_type_mismatch_detected(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [Query(input="bad", output="bad", tag=QueryTag.TYPICAL)]
        }
    )
    issues = validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_TYPE for issue in issues)
    assert any(issue.code == CODE_QUERY_OUTPUT_TYPE for issue in issues)


def test_bool_query_values_are_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(
                    input={"src": True, "dst": 1},
                    output=False,
                    tag=QueryTag.TYPICAL,
                )
            ]
        }
    )
    issues = validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_QUERY_INPUT_TYPE for issue in issues)
    assert any(issue.code == CODE_QUERY_OUTPUT_TYPE for issue in issues)


def test_query_input_out_of_bounds_has_dedicated_code(
    baseline_task: Task,
) -> None:
    spec = GraphQueriesSpec.model_validate(baseline_task.spec, strict=True)
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(
                    input={"src": spec.n_nodes, "dst": 0},
                    output=0,
                    tag=QueryTag.TYPICAL,
                )
            ]
        }
    )
    issues = validate_graph_queries_task(corrupted)
    assert any(
        issue.code == CODE_QUERY_INPUT_BOUNDS
        and issue.location == "queries[0].input"
        for issue in issues
    )


def test_query_output_mismatch_detected(baseline_task: Task) -> None:
    query = baseline_task.queries[0]
    bad_query = Query(
        input=query.input,
        output=query.output + 1,
        tag=query.tag,
    )
    corrupted = baseline_task.model_copy(update={"queries": [bad_query]})
    issues = validate_graph_queries_task(corrupted)
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
    issues = validate_graph_queries_task(corrupted)
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
    issues = validate_graph_queries_task(corrupted)
    assert not any(issue.code == CODE_QUERY_INPUT_DUPLICATE for issue in issues)


def test_semantic_mismatch_detected(baseline_task: Task) -> None:
    spec = GraphQueriesSpec.model_validate(baseline_task.spec, strict=True)
    expected = eval_graph_queries(spec, 0, 0)
    corrupted = baseline_task.model_copy(
        update={"code": f"def f(src, dst):\n    return {expected + 1}"}
    )
    issues = validate_graph_queries_task(
        corrupted,
        axes=GraphQueriesAxes(
            query_types=[spec.query_type],
            directed_choices=[spec.directed],
            weighted_choices=[spec.weighted],
            n_nodes_range=(1, 1),
            edge_count_range=(0, 0),
            weight_range=(1, 1),
            disconnected_prob_range=(0.0, 0.0),
            multi_edge_prob_range=(0.0, 0.0),
            hub_bias_prob_range=(0.0, 0.0),
        ),
        semantic_trials=4,
        max_semantic_issues=4,
        random_seed=123,
    )
    assert any(issue.code == CODE_SEMANTIC_MISMATCH for issue in issues)


def test_semantic_issue_capping(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(src, dst):\n    return 1000000000"}
    )
    issues = validate_graph_queries_task(
        corrupted,
        execute_untrusted_code=True,
        semantic_trials=20,
        max_semantic_issues=3,
        random_seed=123,
    )
    mismatches = [
        issue for issue in issues if issue.code == CODE_SEMANTIC_MISMATCH
    ]
    capped = [
        issue for issue in issues if issue.code == CODE_SEMANTIC_ISSUES_CAPPED
    ]
    assert len(mismatches) == 3
    assert len(capped) == 1


def test_execute_untrusted_code_false_skips_exec_errors(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": "raise ValueError(1)"})
    issues = _validate_graph_queries_task(
        corrupted,
        execute_untrusted_code=False,
    )
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_default_execute_untrusted_code_false_skips_exec_errors(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(src, dst=len(1)):\n    return 0"}
    )
    issues = _validate_graph_queries_task(corrupted)
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_execute_untrusted_code_true_reports_exec_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(src, dst=len(1)):\n    return 0"}
    )
    issues = _validate_graph_queries_task(
        corrupted,
        execute_untrusted_code=True,
    )
    assert any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)


def test_unhashable_spec_reports_task_id_issue_without_raising(
    baseline_task: Task,
) -> None:
    class _Unserializable:
        pass

    corrupted = baseline_task.model_copy(
        update={"spec": {**baseline_task.spec, "x": _Unserializable()}}
    )
    issues = _validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_TASK_ID_MISMATCH for issue in issues)


def test_non_string_python_code_payload_reports_parse_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": {"python": 123}})
    issues = validate_graph_queries_task(corrupted)
    assert any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)


def test_non_python_code_map_skips_python_validation(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "code": {
                "java": "public static long f(int src, int dst) { return 0L; }"
            }
        }
    )
    issues = validate_graph_queries_task(corrupted)
    assert not any(issue.code == CODE_CODE_PARSE_ERROR for issue in issues)
    assert not any(issue.code == CODE_CODE_EXEC_ERROR for issue in issues)
    assert not any(issue.code == CODE_CODE_MISSING_FUNC for issue in issues)


def test_exec_function_is_closed_after_validation(
    baseline_task: Task,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    was_closed = False
    call_count = 0

    def fake_fn(src: int, dst: int) -> int:
        del src, dst
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
        "genfxn.graph_queries.validate.execute_code_restricted",
        _stub_execute,
    )

    validate_graph_queries_task(
        baseline_task,
        execute_untrusted_code=True,
        semantic_trials=1,
        random_seed=123,
    )

    assert call_count >= 1
    assert was_closed is True
