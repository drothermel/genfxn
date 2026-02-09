import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import WRONG_FAMILY, Severity
from genfxn.stack_bytecode.models import StackBytecodeAxes, StackBytecodeSpec
from genfxn.stack_bytecode.render import render_stack_bytecode
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stack_bytecode.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_CODE_RUNTIME_ERROR,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_SPEC_DESERIALIZE_ERROR,
    CODE_TASK_ID_MISMATCH,
    CODE_UNSAFE_AST,
    _validate_ast_whitelist,
    _validate_query_types,
)
from genfxn.stack_bytecode.validate import (
    validate_stack_bytecode_task as _validate_stack_bytecode_task,
)


def validate_stack_bytecode_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_stack_bytecode_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_stack_bytecode_task(rng=random.Random(42))


class TestValidTask:
    def test_generated_task_has_no_errors(self, baseline_task: Task) -> None:
        issues = validate_stack_bytecode_task(baseline_task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    @pytest.mark.full
    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_stack_bytecode_task(rng=random.Random(seed))
            issues = validate_stack_bytecode_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"seed {seed} produced errors: {errors}"


class TestFamilyAndTaskId:
    def test_wrong_family_short_circuits(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(update={"family": "piecewise"})
        issues = validate_stack_bytecode_task(corrupted)
        assert len(issues) == 1
        assert issues[0].code == WRONG_FAMILY

    def test_corrupted_task_id_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"task_id": "stack_bytecode_00000000"}
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)
        assert any(
            i.code == CODE_TASK_ID_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )


class TestSpecDeserialization:
    def test_invalid_spec_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(update={"spec": {"bad": "spec"}})
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)

    def test_query_type_checks_run_even_when_spec_fails(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
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
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)


class TestCodeCompilationAndExecution:
    def test_syntax_error_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return ("}
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_python_code_in_map_syntax_error_caught(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": {"python": "def f(xs):\n    return ("}}
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_non_python_code_map_skips_python_validation(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "code": {
                    "java": (
                        "public static int[] f(int[] xs){"
                        "return new int[]{0,0};}"
                    )
                }
            }
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert not any(i.code == CODE_CODE_PARSE_ERROR for i in issues)
        assert not any(i.code == CODE_CODE_EXEC_ERROR for i in issues)
        assert not any(i.code == CODE_CODE_MISSING_FUNC for i in issues)

    def test_exec_error_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "raise ValueError('boom')"}
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert any(
            i.code in {CODE_CODE_EXEC_ERROR, CODE_UNSAFE_AST} for i in issues
        )

    def test_missing_func_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def g(xs):\n    return (0, 0)"}
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_CODE_MISSING_FUNC for i in issues)

    def test_runtime_error_caught(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return 1/0"}
        )
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)
        assert any(
            "input" in i.message.lower()
            for i in issues
            if i.code == CODE_CODE_RUNTIME_ERROR
        )

    def test_execute_untrusted_code_false_skips_exec(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "raise ValueError('boom')"}
        )
        issues = _validate_stack_bytecode_task(
            corrupted,
            execute_untrusted_code=False,
        )
        assert not any(i.code == CODE_CODE_EXEC_ERROR for i in issues)


class TestQueryTypeValidation:
    def test_non_list_input_error_strict(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(
                        input="bad",
                        output=(0, 0),
                        tag=QueryTag.TYPICAL,
                    )
                ]
            }
        )
        issues = validate_stack_bytecode_task(corrupted, strict=True)
        q_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert q_issues
        assert all(i.severity == Severity.ERROR for i in q_issues)

    def test_non_list_input_warning_lenient(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(
                        input="bad",
                        output=(0, 0),
                        tag=QueryTag.TYPICAL,
                    )
                ]
            }
        )
        issues = validate_stack_bytecode_task(corrupted, strict=False)
        q_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert q_issues
        assert all(i.severity == Severity.WARNING for i in q_issues)

    def test_list_with_non_int_element_detected(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(
                        input=[1, "x"],
                        output=(0, 0),
                        tag=QueryTag.TYPICAL,
                    )
                ]
            }
        )
        issues = validate_stack_bytecode_task(corrupted, strict=True)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_wrong_output_shape_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(input=[1], output=1, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_stack_bytecode_task(corrupted, strict=True)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)

    def test_location_includes_specific_query_index(
        self, baseline_task: Task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(input=[1], output=(0, 0), tag=QueryTag.TYPICAL),
                    Query(input="bad", output=(0, 0), tag=QueryTag.TYPICAL),
                ]
            }
        )
        issues = validate_stack_bytecode_task(corrupted)
        input_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert any("queries[1]" in i.location for i in input_issues)


class TestQueryOutputAndSemantics:
    def test_wrong_query_output_caught(self, baseline_task: Task) -> None:
        query = baseline_task.queries[0]
        assert isinstance(query.output, tuple)
        bad_query = Query(
            input=query.input,
            output=(query.output[0], query.output[1] + 999),
            tag=query.tag,
        )
        corrupted = baseline_task.model_copy(update={"queries": [bad_query]})
        issues = validate_stack_bytecode_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)

    def test_semantic_mismatch_detected(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return (0, 999)"}
        )
        issues = validate_stack_bytecode_task(
            corrupted,
            semantic_trials=5,
            max_semantic_issues=20,
        )
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)

    def test_semantic_issue_capping(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={"code": "def f(xs):\n    return (0, 999)"}
        )
        issues = validate_stack_bytecode_task(
            corrupted,
            semantic_trials=20,
            max_semantic_issues=3,
        )
        mismatches = [i for i in issues if i.code == CODE_SEMANTIC_MISMATCH]
        capped = [i for i in issues if i.code == CODE_SEMANTIC_ISSUES_CAPPED]
        assert len(mismatches) <= 3
        assert len(capped) <= 1


class TestAxesAndParanoidHelpers:
    def test_custom_axes_respected_in_semantic_generation(
        self, baseline_task: Task
    ) -> None:
        axes = StackBytecodeAxes(value_range=(0, 0), list_length_range=(0, 0))
        issues = validate_stack_bytecode_task(
            baseline_task,
            axes=axes,
            semantic_trials=3,
            random_seed=123,
        )
        # Valid baseline task should not fail with constrained axes.
        assert not any(i.severity == Severity.ERROR for i in issues)

    def test_query_types_helper(self, baseline_task: Task) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(input="bad", output=(0, 0), tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = _validate_query_types(corrupted, strict=True)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_ast_whitelist_rejects_import(self) -> None:
        issues, _ = _validate_ast_whitelist(
            "import os\ndef f(xs):\n    return (0, 0)"
        )
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_ast_whitelist_rejects_attribute_call(self) -> None:
        issues, _ = _validate_ast_whitelist(
            "def f(xs):\n    return xs.__class__"
        )
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_ast_whitelist_accepts_stack_renderer_output(self) -> None:
        task = generate_stack_bytecode_task(rng=random.Random(7))
        spec = StackBytecodeSpec.model_validate(task.spec, strict=True)
        issues, _ = _validate_ast_whitelist(render_stack_bytecode(spec))
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)
