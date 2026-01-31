import random

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Severity
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.piecewise.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_CODE_RUNTIME_ERROR,
    CODE_NON_MONOTONIC_THRESHOLDS,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_SPEC_DESERIALIZE_ERROR,
    CODE_TASK_ID_MISMATCH,
    CODE_UNSAFE_AST,
    CODE_UNSUPPORTED_CONDITION,
    validate_piecewise_task,
)


class TestValidTask:
    def test_generated_task_has_no_errors(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        issues = validate_piecewise_task(task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_piecewise_task(rng=random.Random(seed))
            issues = validate_piecewise_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"Seed {seed} produced errors: {errors}"


class TestTaskIdValidation:
    def test_corrupted_task_id_detected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"task_id": "piecewise_00000000"})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)
        assert any(
            i.code == CODE_TASK_ID_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )

    def test_wrong_family_prefix_detected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"task_id": "stateful_" + task.task_id[10:]}
        )
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)


class TestSpecDeserialization:
    def test_invalid_spec_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"spec": {"invalid": "spec"}})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(
            i.code == CODE_SPEC_DESERIALIZE_ERROR
            and i.severity == Severity.ERROR
            for i in issues
        )

    def test_query_type_checks_run_even_when_spec_fails(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "spec": {"invalid": "spec"},
                "queries": [
                    Query(input="not_int", output=0, tag=QueryTag.TYPICAL)
                ],
            }
        )
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)


class TestConditionSupport:
    def test_supported_conditions_pass(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        issues = validate_piecewise_task(task)
        assert not any(i.code == CODE_UNSUPPORTED_CONDITION for i in issues)

    def test_unsupported_condition_gt_detected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Replace first branch condition with gt (unsupported)
        spec = dict(task.spec)
        spec["branches"] = list(spec["branches"])
        spec["branches"][0] = dict(spec["branches"][0])
        spec["branches"][0]["condition"] = {"kind": "gt", "value": 0}
        corrupted = task.model_copy(update={"spec": spec})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_UNSUPPORTED_CONDITION for i in issues)
        assert any(
            i.code == CODE_UNSUPPORTED_CONDITION
            and i.severity == Severity.ERROR
            for i in issues
        )

    def test_unsupported_condition_even_detected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        spec = dict(task.spec)
        spec["branches"] = list(spec["branches"])
        spec["branches"][0] = dict(spec["branches"][0])
        spec["branches"][0]["condition"] = {"kind": "even"}
        corrupted = task.model_copy(update={"spec": spec})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_UNSUPPORTED_CONDITION for i in issues)

    def test_location_includes_branch_index(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        spec = dict(task.spec)
        spec["branches"] = list(spec["branches"])
        # Corrupt second branch if it exists, otherwise first
        idx = min(1, len(spec["branches"]) - 1)
        spec["branches"][idx] = dict(spec["branches"][idx])
        spec["branches"][idx]["condition"] = {"kind": "odd"}
        corrupted = task.model_copy(update={"spec": spec})
        issues = validate_piecewise_task(corrupted)
        unsupported = [
            i for i in issues if i.code == CODE_UNSUPPORTED_CONDITION
        ]
        assert any(f"branches[{idx}]" in i.location for i in unsupported)

    def test_message_includes_supported_kinds(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        spec = dict(task.spec)
        spec["branches"] = list(spec["branches"])
        spec["branches"][0] = dict(spec["branches"][0])
        spec["branches"][0]["condition"] = {"kind": "ge", "value": 5}
        corrupted = task.model_copy(update={"spec": spec})
        issues = validate_piecewise_task(corrupted)
        unsupported = [
            i for i in issues if i.code == CODE_UNSUPPORTED_CONDITION
        ]
        assert len(unsupported) == 1
        assert "le" in unsupported[0].message
        assert "lt" in unsupported[0].message


class TestCodeCompilation:
    def test_syntax_error_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(x):\n    return ("})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)
        assert any(
            i.code == CODE_CODE_PARSE_ERROR and i.severity == Severity.ERROR
            for i in issues
        )

    def test_exec_error_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Code that raises at module exec time (not at call time)
        corrupted = task.model_copy(update={"code": "raise ValueError('boom')"})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_CODE_EXEC_ERROR for i in issues)

    def test_missing_func_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def g(x):\n    return x"})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_CODE_MISSING_FUNC for i in issues)
        assert any(
            i.code == CODE_CODE_MISSING_FUNC and i.severity == Severity.ERROR
            for i in issues
        )


class TestCodeRuntime:
    def test_runtime_error_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    raise ZeroDivisionError('oops')"}
        )
        issues = validate_piecewise_task(corrupted, value_range=(0, 2))
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)
        assert any(
            i.code == CODE_CODE_RUNTIME_ERROR and i.severity == Severity.ERROR
            for i in issues
        )

    def test_runtime_error_includes_x_value(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    return 1 // x"}  # Fails at x=0
        )
        issues = validate_piecewise_task(corrupted, value_range=(-1, 1))
        runtime_errors = [
            i for i in issues if i.code == CODE_CODE_RUNTIME_ERROR
        ]
        assert any("f(0)" in i.message for i in runtime_errors)


class TestQueryTypeValidation:
    def test_non_int_input_is_error_strict(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_piecewise_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_non_int_input_is_warning_lenient(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_piecewise_task(corrupted, strict=False)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.WARNING for i in type_issues)

    def test_non_int_output_is_error_strict(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "queries": [Query(input=0, output="text", tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_piecewise_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_float_input_detected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "queries": [Query(input=3.14, output=0, tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_location_includes_query_index(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=0, output=0, tag=QueryTag.TYPICAL),
                    Query(input="bad", output=0, tag=QueryTag.TYPICAL),
                ]
            }
        )
        issues = validate_piecewise_task(corrupted)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert any("queries[1]" in i.location for i in type_issues)


class TestQueryOutputValidation:
    def test_wrong_output_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        first_query = task.queries[0]
        wrong_query = Query(
            input=first_query.input,
            output=first_query.output + 999,  # Definitely wrong
            tag=first_query.tag,
        )
        corrupted = task.model_copy(update={"queries": [wrong_query]})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)
        assert any(
            i.code == CODE_QUERY_OUTPUT_MISMATCH
            and i.severity == Severity.ERROR
            for i in issues
        )

    def test_location_includes_specific_query_index(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        assert len(task.queries) >= 2
        # Keep first query valid, corrupt second
        queries = list(task.queries[:2])
        queries[1] = Query(
            input=queries[1].input,
            output=queries[1].output + 999,
            tag=queries[1].tag,
        )
        corrupted = task.model_copy(update={"queries": queries})
        issues = validate_piecewise_task(corrupted)
        mismatch_issues = [
            i for i in issues if i.code == CODE_QUERY_OUTPUT_MISMATCH
        ]
        assert any("queries[1]" in i.location for i in mismatch_issues)


class TestSemanticValidation:
    def test_code_differing_from_spec_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Replace with code that returns a constant
        corrupted = task.model_copy(update={"code": "def f(x):\n    return 0"})
        issues = validate_piecewise_task(corrupted, value_range=(0, 5))
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)

    def test_semantic_error_includes_x_value(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(x):\n    return 0"})
        issues = validate_piecewise_task(corrupted, value_range=(0, 2))
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        # Should have x value in message like "f(0) = 0, expected X"
        assert all(
            "f(" in i.message and ")" in i.message for i in semantic_issues
        )


class TestNonMonotonicThresholds:
    def test_non_monotonic_emits_warning_not_error(self) -> None:
        # Generate tasks until we find one with non-monotonic thresholds
        # or create one manually by modifying the spec
        task = generate_piecewise_task(rng=random.Random(42))
        issues = validate_piecewise_task(task)
        monotonic_issues = [
            i for i in issues if i.code == CODE_NON_MONOTONIC_THRESHOLDS
        ]
        # All such issues should be warnings
        assert all(i.severity == Severity.WARNING for i in monotonic_issues)

    def test_monotonic_thresholds_no_warning(self) -> None:
        # Most generated tasks should have monotonic thresholds
        # since the sampler picks distinct values from threshold_range
        found_monotonic = False
        for seed in range(100):
            task = generate_piecewise_task(rng=random.Random(seed))
            issues = validate_piecewise_task(task)
            monotonic_issues = [
                i for i in issues if i.code == CODE_NON_MONOTONIC_THRESHOLDS
            ]
            if not monotonic_issues:
                found_monotonic = True
                break
        assert found_monotonic, (
            "Could not find a task with monotonic thresholds"
        )


class TestEmitDiagnostics:
    def test_diagnostics_emitted_by_default(self) -> None:
        # Create a task with non-monotonic thresholds
        task = generate_piecewise_task(rng=random.Random(42))
        spec = dict(task.spec)
        spec["branches"] = list(spec["branches"])
        if len(spec["branches"]) >= 2:
            # Swap threshold order to make non-monotonic
            spec["branches"][0] = dict(spec["branches"][0])
            spec["branches"][1] = dict(spec["branches"][1])
            cond0 = dict(spec["branches"][0]["condition"])
            cond1 = dict(spec["branches"][1]["condition"])
            if "value" in cond0 and "value" in cond1:
                # Make second threshold smaller than first
                cond0["value"], cond1["value"] = 10, 5
                spec["branches"][0]["condition"] = cond0
                spec["branches"][1]["condition"] = cond1
                corrupted = task.model_copy(update={"spec": spec})
                issues = validate_piecewise_task(corrupted)
                assert any(
                    i.code == CODE_NON_MONOTONIC_THRESHOLDS for i in issues
                )

    def test_diagnostics_suppressed_when_false(self) -> None:
        # Create a task with non-monotonic thresholds
        task = generate_piecewise_task(rng=random.Random(42))
        spec = dict(task.spec)
        spec["branches"] = list(spec["branches"])
        if len(spec["branches"]) >= 2:
            spec["branches"][0] = dict(spec["branches"][0])
            spec["branches"][1] = dict(spec["branches"][1])
            cond0 = dict(spec["branches"][0]["condition"])
            cond1 = dict(spec["branches"][1]["condition"])
            if "value" in cond0 and "value" in cond1:
                cond0["value"], cond1["value"] = 10, 5
                spec["branches"][0]["condition"] = cond0
                spec["branches"][1]["condition"] = cond1
                corrupted = task.model_copy(update={"spec": spec})
                # With emit_diagnostics=False, no NON_MONOTONIC_THRESHOLDS
                issues = validate_piecewise_task(
                    corrupted, emit_diagnostics=False
                )
                assert not any(
                    i.code == CODE_NON_MONOTONIC_THRESHOLDS for i in issues
                )

    def test_correctness_errors_still_emitted_when_diagnostics_off(
        self,
    ) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Corrupt the code - this is a correctness error, not a diagnostic
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    return 999999"}
        )
        issues = validate_piecewise_task(
            corrupted, value_range=(0, 5), emit_diagnostics=False
        )
        # Semantic mismatch errors should still be present
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)

    def test_semantic_capped_warning_still_emitted_when_diagnostics_off(
        self,
    ) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    return 999999"}
        )
        issues = validate_piecewise_task(
            corrupted,
            value_range=(-100, 100),
            max_semantic_issues=5,
            emit_diagnostics=False,
        )
        # SEMANTIC_ISSUES_CAPPED is operational, not diagnostic - should still emit
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)


class TestValueRangeDefault:
    def test_uses_axes_default_when_none(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Should run without error using default value_range
        issues = validate_piecewise_task(task, value_range=None)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_custom_value_range_respected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Use a very small range
        issues = validate_piecewise_task(task, value_range=(0, 1))
        # Should still validate without errors for a valid task
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []


class TestSemanticIssueCapping:
    def test_caps_semantic_mismatch_issues(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Code that always returns wrong value - would fail for all 201 inputs
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    return 999999"}
        )
        issues = validate_piecewise_task(corrupted, value_range=(-100, 100))
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        # Should be capped at default of 10
        assert len(semantic_issues) == 10
        # Should have capped warning
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_caps_runtime_errors(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Code that always raises
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    raise ValueError('boom')"}
        )
        issues = validate_piecewise_task(
            corrupted, value_range=(0, 50), max_semantic_issues=5
        )
        runtime_issues = [
            i for i in issues if i.code == CODE_CODE_RUNTIME_ERROR
        ]
        assert len(runtime_issues) == 5
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_capped_warning_is_warning_severity(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(x):\n    return 0"})
        issues = validate_piecewise_task(
            corrupted, value_range=(0, 20), max_semantic_issues=3
        )
        capped = [i for i in issues if i.code == CODE_SEMANTIC_ISSUES_CAPPED]
        assert len(capped) == 1
        assert capped[0].severity == Severity.WARNING

    def test_custom_cap_respected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(x):\n    return 0"})
        issues = validate_piecewise_task(
            corrupted, value_range=(0, 100), max_semantic_issues=3
        )
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        assert len(semantic_issues) == 3

    def test_zero_cap_means_unlimited(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    return 999999"}
        )
        # Small range to keep test fast
        issues = validate_piecewise_task(
            corrupted, value_range=(0, 20), max_semantic_issues=0
        )
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        # Should have all 21 issues (0 through 20 inclusive)
        assert len(semantic_issues) == 21
        # No capped warning
        assert not any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_no_cap_warning_when_under_limit(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(x):\n    return 0"})
        # Only 3 values to check, cap is 10
        issues = validate_piecewise_task(
            corrupted, value_range=(0, 2), max_semantic_issues=10
        )
        # Should not emit capped warning since we didn't hit the limit
        assert not any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)


def _make_task_with_code(code: str) -> Task:
    """Create a task with custom code for testing AST validation."""
    task = generate_piecewise_task(rng=random.Random(42))
    return task.model_copy(update={"code": code})


class TestParanoidMode:
    """Test AST whitelist validation in paranoid mode."""

    def test_valid_generated_code_passes(self) -> None:
        """Generated piecewise code should pass paranoid check."""
        task = generate_piecewise_task(rng=random.Random(42))
        issues = validate_piecewise_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_import_rejected(self) -> None:
        """Import statements should be rejected."""
        task = _make_task_with_code("import os\ndef f(x): return x")
        issues = validate_piecewise_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert len(unsafe) >= 1
        assert "Import" in unsafe[0].message

    def test_attribute_access_rejected(self) -> None:
        """Attribute access should be rejected."""
        task = _make_task_with_code("def f(x): return x.__class__")
        issues = validate_piecewise_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_disallowed_call_rejected(self) -> None:
        """Calls other than abs() should be rejected."""
        task = _make_task_with_code("def f(x): return len([x])")
        issues = validate_piecewise_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_abs_with_multiple_args_rejected(self) -> None:
        """abs() with wrong arity should be rejected."""
        task = _make_task_with_code("def f(x): return abs(x, 1)")
        issues = validate_piecewise_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_abs_call_allowed(self) -> None:
        """abs(x) calls should be allowed."""
        code = (
            "def f(x):\n"
            "    if x < 0:\n"
            "        return abs(x)\n"
            "    else:\n"
            "        return x"
        )
        task = _make_task_with_code(code)
        issues = validate_piecewise_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_disallowed_name_rejected(self) -> None:
        """Names other than x and abs should be rejected."""
        task = _make_task_with_code("def f(x): return open")
        issues = validate_piecewise_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert any("open" in i.message for i in unsafe)

    def test_error_includes_line_number(self) -> None:
        """AST errors should include line numbers."""
        task = _make_task_with_code("import os\ndef f(x): return x")
        issues = validate_piecewise_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert any("line" in i.message for i in unsafe)

    def test_paranoid_false_allows_unsafe_code(self) -> None:
        """Without paranoid mode, unsafe code is not flagged as UNSAFE_AST."""
        task = _make_task_with_code("import os\ndef f(x): return x")
        issues = validate_piecewise_task(task, paranoid=False)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_multiple_seeds_pass_paranoid(self) -> None:
        """Multiple generated tasks should all pass paranoid check."""
        for seed in [1, 42, 123, 999]:
            task = generate_piecewise_task(rng=random.Random(seed))
            issues = validate_piecewise_task(task, paranoid=True)
            assert not any(i.code == CODE_UNSAFE_AST for i in issues), (
                f"Seed {seed} produced UNSAFE_AST issues"
            )
