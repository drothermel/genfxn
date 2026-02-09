import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task

validate_module = pytest.importorskip("genfxn.stack_bytecode.validate")
task_module = pytest.importorskip("genfxn.stack_bytecode.task")


_validate_stack_bytecode_task = getattr(
    validate_module,
    "validate_stack_bytecode_task",
    None,
)
if not callable(_validate_stack_bytecode_task):
    pytest.skip(
        "validate_stack_bytecode_task is not available",
        allow_module_level=True,
    )


generate_stack_bytecode_task = getattr(
    task_module,
    "generate_stack_bytecode_task",
    None,
)
if not callable(generate_stack_bytecode_task):
    pytest.skip(
        "generate_stack_bytecode_task is not available",
        allow_module_level=True,
    )


def validate_stack_bytecode_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_stack_bytecode_task(*args, **kwargs)


def _codes(issues: list[Any]) -> list[str]:
    return [str(issue.code) for issue in issues]


def _has_code(issues: list[Any], snippet: str) -> bool:
    token = snippet.lower()
    return any(token in str(issue.code).lower() for issue in issues)


@pytest.fixture
def baseline_task() -> Task:
    return generate_stack_bytecode_task(rng=random.Random(42))


class TestValidTask:
    def test_generated_task_has_no_structural_errors(
        self, baseline_task: Task
    ) -> None:
        issues = validate_stack_bytecode_task(baseline_task)
        codes = _codes(issues)
        assert "TASK_ID_MISMATCH" not in codes
        assert "SPEC_DESERIALIZE_ERROR" not in codes
        assert "CODE_QUERY_INPUT_TYPE" not in codes
        assert "CODE_QUERY_OUTPUT_TYPE" not in codes

    @pytest.mark.full
    def test_multiple_seeds_have_no_structural_errors(self) -> None:
        for seed in [1, 7, 42, 123]:
            task = generate_stack_bytecode_task(rng=random.Random(seed))
            issues = validate_stack_bytecode_task(task)
            codes = _codes(issues)
            assert "TASK_ID_MISMATCH" not in codes, (
                f"seed {seed} produced TASK_ID_MISMATCH: {codes}"
            )
            assert "SPEC_DESERIALIZE_ERROR" not in codes, (
                f"seed {seed} produced SPEC_DESERIALIZE_ERROR: {codes}"
            )


class TestIssueCodesAndBehavior:
    def test_task_id_mismatch_is_detected(self, baseline_task: Task) -> None:
        bad = baseline_task.model_copy(update={"task_id": "stack_00000000"})
        issues = validate_stack_bytecode_task(bad)
        assert _has_code(issues, "task_id_mismatch")

    def test_spec_deserialize_error_is_reported(
        self, baseline_task: Task
    ) -> None:
        bad = baseline_task.model_copy(update={"spec": {"bad": "spec"}})
        issues = validate_stack_bytecode_task(bad)
        assert _has_code(issues, "spec_deserialize_error")

    def test_query_type_validation_runs_even_with_bad_spec(
        self, baseline_task: Task
    ) -> None:
        bad = baseline_task.model_copy(
            update={
                "spec": {"bad": "spec"},
                "queries": [
                    Query(
                        input="bad_input",
                        output="bad_output",
                        tag=QueryTag.TYPICAL,
                    )
                ],
            }
        )
        issues = validate_stack_bytecode_task(bad)
        assert _has_code(issues, "spec_deserialize_error")

    def test_code_parse_error_is_reported(self, baseline_task: Task) -> None:
        bad = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return ("}
        )
        issues = validate_stack_bytecode_task(bad)
        assert _has_code(issues, "code_parse_error")

    def test_missing_function_is_reported(self, baseline_task: Task) -> None:
        bad = baseline_task.model_copy(
            update={"code": "def g(xs):\n    return 0"}
        )
        issues = validate_stack_bytecode_task(bad)
        assert _has_code(issues, "code_missing_func")

    def test_query_output_mismatch_is_reported(
        self, baseline_task: Task
    ) -> None:
        query = baseline_task.queries[0]
        output = query.output
        assert isinstance(output, tuple)
        assert len(output) == 2
        assert isinstance(output[0], int)
        assert isinstance(output[1], int)
        bad_query = Query(
            input=query.input,
            output=(output[0], output[1] + 99),
            tag=query.tag,
        )
        bad = baseline_task.model_copy(update={"queries": [bad_query]})
        issues = validate_stack_bytecode_task(bad)
        assert _has_code(issues, "query_output_mismatch")

    def test_semantic_issue_capping_behavior(self, baseline_task: Task) -> None:
        bad = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return 0"}
        )
        issues = validate_stack_bytecode_task(bad, semantic_trials=3)
        semantic = [
            issue
            for issue in issues
            if "semantic_mismatch" in str(issue.code).lower()
        ]
        assert len(semantic) <= 3
