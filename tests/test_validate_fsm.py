import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import WRONG_FAMILY, Severity
from genfxn.fsm.task import generate_fsm_task
from genfxn.fsm.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_CODE_RUNTIME_ERROR,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_MISMATCH,
    CODE_SPEC_DESERIALIZE_ERROR,
    CODE_TASK_ID_MISMATCH,
    CODE_UNSAFE_AST,
    _validate_ast_whitelist,
)
from genfxn.fsm.validate import validate_fsm_task as _validate_fsm_task


def validate_fsm_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_fsm_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_fsm_task(rng=random.Random(42))


class TestValidTask:
    def test_generated_task_has_no_errors(self, baseline_task: Task) -> None:
        issues = validate_fsm_task(baseline_task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    @pytest.mark.full
    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_fsm_task(rng=random.Random(seed))
            issues = validate_fsm_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"seed {seed} produced errors: {errors}"

    @pytest.mark.full
    def test_fuzz_many_generated_tasks_no_errors(self) -> None:
        rng = random.Random(1337)
        for _ in range(120):
            task = generate_fsm_task(rng=rng)
            issues = validate_fsm_task(
                task,
                execute_untrusted_code=True,
                semantic_trials=20,
                max_semantic_issues=20,
                random_seed=17,
            )
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == []

    @pytest.mark.full
    def test_fuzz_rendered_code_stays_ast_safe(self) -> None:
        rng = random.Random(2026)
        for _ in range(200):
            task = generate_fsm_task(rng=rng)
            assert isinstance(task.code, str)
            issues, _ = _validate_ast_whitelist(task.code)
            unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
            assert unsafe == []


class TestFamilyAndTaskId:
    def test_wrong_family_short_circuits(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(update={"family": "piecewise"})
        issues = validate_fsm_task(corrupted)
        assert len(issues) == 1
        assert issues[0].code == WRONG_FAMILY

    def test_corrupted_task_id_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(update={"task_id": "fsm_00000000"})
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)


class TestSpecAndCodeValidation:
    def test_invalid_spec_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(update={"spec": {"bad": "spec"}})
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)

    def test_syntax_error_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return ("}
        )
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_non_python_code_map_skips_python_validation(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "code": {
                    "java": "public static int f(int[] xs){return 0;}"
                }
            }
        )
        issues = validate_fsm_task(corrupted)
        assert not any(i.code == CODE_CODE_PARSE_ERROR for i in issues)
        assert not any(i.code == CODE_CODE_EXEC_ERROR for i in issues)
        assert not any(i.code == CODE_CODE_MISSING_FUNC for i in issues)

    def test_non_string_python_code_payload_reports_parse_error(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(update={"code": {"python": 123}})
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_runtime_error_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return 1 // 0"}
        )
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)

    def test_unsafe_ast_short_circuits_execution(
        self, baseline_task: Task, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        called = False

        def _spy(*args: Any, **kwargs: Any) -> dict[str, Any]:
            nonlocal called
            called = True
            return {}

        monkeypatch.setattr("genfxn.fsm.validate.execute_code_restricted", _spy)
        corrupted = baseline_task.model_copy(
            update={"code": "while True:\n    pass\ndef f(xs):\n    return 0"}
        )
        issues = _validate_fsm_task(corrupted, execute_untrusted_code=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)
        assert not any(i.code == CODE_CODE_EXEC_ERROR for i in issues)
        assert called is False


class TestQueryAndSemantics:
    def test_query_input_type_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(input="bad", output=0, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_query_output_type_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(
                        input=[1],
                        output="bad",
                        tag=QueryTag.TYPICAL,
                    )
                ]
            }
        )
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)

    def test_bool_query_values_are_rejected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(
                        input=[True, 1],
                        output=False,
                        tag=QueryTag.TYPICAL,
                    )
                ]
            }
        )
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)

    def test_wrong_query_output_caught(self, baseline_task: Task) -> None:
        query = baseline_task.queries[0]
        bad_query = Query(
            input=query.input,
            output=query.output + 999,
            tag=query.tag,
        )
        corrupted = baseline_task.model_copy(update={"queries": [bad_query]})
        issues = validate_fsm_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)

    def test_semantic_mismatch_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return 0"}
        )
        issues = validate_fsm_task(
            corrupted,
            semantic_trials=8,
            max_semantic_issues=8,
        )
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)


class TestAstSafety:
    def test_generated_code_passes_ast_whitelist(
        self, baseline_task: Task
    ) -> None:
        assert isinstance(baseline_task.code, str)
        issues, _ = _validate_ast_whitelist(baseline_task.code)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_import_is_rejected(self) -> None:
        code = "def f(xs):\n    import os\n    return 0\n"
        issues, _ = _validate_ast_whitelist(code)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)
