import random

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Severity
from genfxn.stateful.task import generate_stateful_task
from genfxn.stateful.validate import (
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
    validate_stateful_task,
)


@pytest.fixture
def baseline_task() -> Task:
    return generate_stateful_task(rng=random.Random(42))


class TestValidTask:
    def test_generated_task_has_no_errors(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        issues = validate_stateful_task(task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    @pytest.mark.full
    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_stateful_task(rng=random.Random(seed))
            issues = validate_stateful_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"Seed {seed} produced errors: {errors}"


class TestTaskIdValidation:
    def test_corrupted_task_id_detected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"task_id": "stateful_00000000"})
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)
        assert any(
            i.code == CODE_TASK_ID_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )

    def test_wrong_family_prefix_detected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"task_id": "piecewise_" + task.task_id[9:]}
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)


class TestSpecDeserialization:
    def test_invalid_spec_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"spec": {"invalid": "spec"}})
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(
            i.code == CODE_SPEC_DESERIALIZE_ERROR
            and i.severity == Severity.ERROR
            for i in issues
        )

    def test_query_type_checks_run_even_when_spec_fails(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "spec": {"invalid": "spec"},
                "queries": [
                    Query(input="not_list", output=0, tag=QueryTag.TYPICAL)
                ],
            }
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_wrong_template_discriminator(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"spec": {"template": "nonexistent_template"}}
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)


class TestCodeCompilation:
    def test_syntax_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return ("}}
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)
        assert any(
            i.code == CODE_CODE_PARSE_ERROR and i.severity == Severity.ERROR
            for i in issues
        )

    def test_exec_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "raise ValueError('boom')"}}
        )
        issues = validate_stateful_task(corrupted)
        assert any(
            i.code in {CODE_CODE_EXEC_ERROR, CODE_UNSAFE_AST} for i in issues
        )

    def test_missing_func_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def g(xs):\n    return 0"}}
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_CODE_MISSING_FUNC for i in issues)
        assert any(
            i.code == CODE_CODE_MISSING_FUNC and i.severity == Severity.ERROR
            for i in issues
        )


class TestCodeRuntime:
    def test_runtime_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 1 % 0"}}
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)
        assert any(
            i.code == CODE_CODE_RUNTIME_ERROR and i.severity == Severity.ERROR
            for i in issues
        )

    def test_runtime_error_includes_input(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 1 % 0"}}
        )
        issues = validate_stateful_task(corrupted)
        runtime_errors = [
            i for i in issues if i.code == CODE_CODE_RUNTIME_ERROR
        ]
        assert any("f(" in i.message for i in runtime_errors)


class TestQueryTypeValidation:
    def test_non_list_input_is_error_strict(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_stateful_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_list_with_non_int_element_is_error(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, "two", 3], output=0, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_stateful_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert any("input[1]" in i.location for i in type_issues)

    def test_non_int_output_is_error_strict(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, 2], output="text", tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_stateful_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_float_output_detected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, 2], output=3.14, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)

    def test_location_includes_query_index(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, 2], output=0, tag=QueryTag.TYPICAL),
                    Query(input="bad", output=0, tag=QueryTag.TYPICAL),
                ]
            }
        )
        issues = validate_stateful_task(corrupted)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert any("queries[1]" in i.location for i in type_issues)


class TestHelperLevelValidation:
    def test_query_types_helper_without_full_pipeline(
        self, baseline_task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(input=[1, "two", 3], output=0, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = _validate_query_types(corrupted, strict=True)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_ast_whitelist_helper_without_execution(self) -> None:
        issues, _ = _validate_ast_whitelist("import os\ndef f(xs): return 0")
        assert any(i.code == CODE_UNSAFE_AST for i in issues)


class TestQueryOutputValidation:
    def test_wrong_output_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        first_query = task.queries[0]
        wrong_query = Query(
            input=first_query.input,
            output=first_query.output + 999,  # Definitely wrong
            tag=first_query.tag,
        )
        corrupted = task.model_copy(update={"queries": [wrong_query]})
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)
        assert any(
            i.code == CODE_QUERY_OUTPUT_MISMATCH
            and i.severity == Severity.ERROR
            for i in issues
        )

    def test_location_includes_specific_query_index(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        assert len(task.queries) >= 2
        # Keep first query valid, corrupt second
        queries = list(task.queries[:2])
        queries[1] = Query(
            input=queries[1].input,
            output=queries[1].output + 999,
            tag=queries[1].tag,
        )
        corrupted = task.model_copy(update={"queries": queries})
        issues = validate_stateful_task(corrupted)
        mismatch_issues = [
            i for i in issues if i.code == CODE_QUERY_OUTPUT_MISMATCH
        ]
        assert any("queries[1]" in i.location for i in mismatch_issues)


class TestSemanticValidation:
    def test_code_differing_from_spec_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        # Replace with code that returns a constant
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 0"}}
        )
        issues = validate_stateful_task(corrupted)
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)

    def test_semantic_error_includes_input(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 0"}}
        )
        issues = validate_stateful_task(corrupted)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        # Should have input in message like "f([...]) = 0, expected X"
        assert all(
            "f(" in i.message and ")" in i.message for i in semantic_issues
        )

    def test_deterministic_with_same_seed(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 0"}}
        )
        issues1 = validate_stateful_task(corrupted, rng=random.Random(123))
        issues2 = validate_stateful_task(corrupted, rng=random.Random(123))
        # Messages should be identical with same seed
        msgs1 = [i.message for i in issues1 if i.code == CODE_SEMANTIC_MISMATCH]
        msgs2 = [i.message for i in issues2 if i.code == CODE_SEMANTIC_MISMATCH]
        assert msgs1 == msgs2


class TestSemanticIssueCapping:
    def test_caps_semantic_mismatch_issues(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 999999"}}
        )
        issues = validate_stateful_task(corrupted)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        # Should be capped at default of 10
        assert len(semantic_issues) == 10
        # Should have capped warning
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_caps_runtime_errors(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 1 % 0"}}
        )
        issues = validate_stateful_task(corrupted, max_semantic_issues=5)
        runtime_issues = [
            i for i in issues if i.code == CODE_CODE_RUNTIME_ERROR
        ]
        assert len(runtime_issues) == 5
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_capped_warning_is_warning_severity(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 0"}}
        )
        issues = validate_stateful_task(corrupted, max_semantic_issues=3)
        capped = [i for i in issues if i.code == CODE_SEMANTIC_ISSUES_CAPPED]
        assert len(capped) == 1
        assert capped[0].severity == Severity.WARNING

    def test_custom_cap_respected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 0"}}
        )
        issues = validate_stateful_task(corrupted, max_semantic_issues=3)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        assert len(semantic_issues) == 3

    def test_zero_cap_means_unlimited(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": {"python": "def f(xs):\n    return 999999"}}
        )
        issues = validate_stateful_task(corrupted, max_semantic_issues=0)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        # With 50 test inputs and all wrong, should have all 50 issues
        assert len(semantic_issues) == 50
        # No capped warning
        assert not any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_no_cap_warning_when_under_limit(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        # Code that only fails on empty list
        code = "def f(xs):\n    return 0 if xs else 999"
        corrupted = task.model_copy(update={"code": {"python": code}})
        issues = validate_stateful_task(corrupted, max_semantic_issues=10)
        # Should not emit capped warning since we didn't hit the limit
        # (only empty list returns 999, which may or may not be wrong)
        capped = [i for i in issues if i.code == CODE_SEMANTIC_ISSUES_CAPPED]
        # This test verifies the cap warning logic works correctly
        if len([i for i in issues if i.code == CODE_SEMANTIC_MISMATCH]) < 10:
            assert capped == []


class TestAxesDefault:
    def test_uses_default_axes_when_none(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        issues = validate_stateful_task(task, axes=None)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_custom_axes_respected(self) -> None:
        from genfxn.stateful.models import StatefulAxes

        axes = StatefulAxes(
            value_range=(-10, 10),
            list_length_range=(1, 5),
        )
        task = generate_stateful_task(axes=axes, rng=random.Random(42))
        issues = validate_stateful_task(task, axes=axes)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []


def _make_task_with_code(code: str) -> Task:
    """Create a task with custom code for testing AST validation."""
    task = generate_stateful_task(rng=random.Random(42))
    return task.model_copy(update={"code": {"python": code}})


@pytest.mark.slow
class TestParanoidMode:
    """Test AST whitelist validation in paranoid mode."""

    def test_valid_generated_code_passes(self, baseline_task) -> None:
        """Generated stateful code should pass paranoid check."""
        task = baseline_task.model_copy(deep=True)
        issues = validate_stateful_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_import_rejected(self) -> None:
        """Import statements should be rejected."""
        task = _make_task_with_code("import os\ndef f(xs): return 0")
        issues = validate_stateful_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert len(unsafe) >= 1
        assert "Import" in unsafe[0].message

    def test_attribute_access_rejected(self) -> None:
        """Attribute access should be rejected."""
        task = _make_task_with_code("def f(xs): return xs.__class__")
        issues = validate_stateful_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_disallowed_call_rejected(self) -> None:
        """Calls other than allowed functions should be rejected."""
        task = _make_task_with_code("def f(xs): return len(xs)")
        issues = validate_stateful_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_max_with_wrong_arity_rejected(self) -> None:
        """max() with wrong arity should be rejected."""
        task = _make_task_with_code(
            "def f(xs): return max(xs)"
        )  # 1 arg not allowed
        issues = validate_stateful_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_abs_call_allowed(self) -> None:
        """abs(x) calls should be allowed."""
        code = (
            "def f(xs: list[int]) -> int:\n"
            "    acc = 0\n"
            "    for x in xs:\n"
            "        acc += abs(x)\n"
            "    return acc"
        )
        task = _make_task_with_code(code)
        issues = validate_stateful_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_max_call_allowed(self) -> None:
        """max(a, b) calls should be allowed."""
        code = (
            "def f(xs: list[int]) -> int:\n"
            "    best_sum = 0\n"
            "    for x in xs:\n"
            "        best_sum = max(best_sum, x)\n"
            "    return best_sum"
        )
        task = _make_task_with_code(code)
        issues = validate_stateful_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_disallowed_name_rejected(self) -> None:
        """Names other than allowed ones should be rejected."""
        task = _make_task_with_code("def f(xs): return open")
        issues = validate_stateful_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert any("open" in i.message for i in unsafe)

    def test_error_includes_line_number(self) -> None:
        """AST errors should include line numbers."""
        task = _make_task_with_code("import os\ndef f(xs): return 0")
        issues = validate_stateful_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert any("line" in i.message for i in unsafe)

    def test_unsafe_code_rejected_without_paranoid_flag(self) -> None:
        """Unsafe code should be rejected even when paranoid=False."""
        task = _make_task_with_code("import os\ndef f(xs): return 0")
        issues = validate_stateful_task(task, paranoid=False)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    @pytest.mark.full
    def test_multiple_seeds_pass_paranoid(self) -> None:
        """Multiple generated tasks should all pass paranoid check."""
        for seed in [1, 42, 123, 999]:
            task = generate_stateful_task(rng=random.Random(seed))
            issues = validate_stateful_task(task, paranoid=True)
            assert not any(i.code == CODE_UNSAFE_AST for i in issues), (
                f"Seed {seed} produced UNSAFE_AST issues"
            )


class TestEachTemplate:
    """Test that each stateful template validates correctly."""

    def test_conditional_linear_sum_valid(self) -> None:
        from genfxn.stateful.models import StatefulAxes, TemplateType

        axes = StatefulAxes(templates=[TemplateType.CONDITIONAL_LINEAR_SUM])
        task = generate_stateful_task(axes=axes, rng=random.Random(42))
        issues = validate_stateful_task(task, axes=axes, paranoid=True)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == [], f"Errors: {errors}"

    def test_resetting_best_prefix_sum_valid(self) -> None:
        from genfxn.stateful.models import StatefulAxes, TemplateType

        axes = StatefulAxes(templates=[TemplateType.RESETTING_BEST_PREFIX_SUM])
        task = generate_stateful_task(axes=axes, rng=random.Random(42))
        issues = validate_stateful_task(task, axes=axes, paranoid=True)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == [], f"Errors: {errors}"

    def test_longest_run_valid(self) -> None:
        from genfxn.stateful.models import StatefulAxes, TemplateType

        axes = StatefulAxes(templates=[TemplateType.LONGEST_RUN])
        task = generate_stateful_task(axes=axes, rng=random.Random(42))
        issues = validate_stateful_task(task, axes=axes, paranoid=True)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == [], f"Errors: {errors}"
