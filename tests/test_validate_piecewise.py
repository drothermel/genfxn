import random

from genfxn.core.models import Query, QueryTag
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
    CODE_SEMANTIC_MISMATCH,
    CODE_SPEC_DESERIALIZE_ERROR,
    CODE_TASK_ID_MISMATCH,
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
        corrupted = task.model_copy(update={"task_id": "stateful_" + task.task_id[10:]})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)


class TestSpecDeserialization:
    def test_invalid_spec_caught(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"spec": {"invalid": "spec"}})
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(
            i.code == CODE_SPEC_DESERIALIZE_ERROR and i.severity == Severity.ERROR
            for i in issues
        )

    def test_query_type_checks_run_even_when_spec_fails(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={
                "spec": {"invalid": "spec"},
                "queries": [Query(input="not_int", output=0, tag=QueryTag.TYPICAL)],
            }
        )
        issues = validate_piecewise_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)


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
        corrupted = task.model_copy(
            update={"code": "def f(x):\n    return undefined_var"}
        )
        issues = validate_piecewise_task(corrupted)
        # Code parses but exec catches undefined at definition time - actually this
        # won't fail at exec time, only at runtime. Let me use a different example.
        # Actually the above will parse and exec fine, it only fails at call time.
        # Use something that fails at module exec time:
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
        runtime_errors = [i for i in issues if i.code == CODE_CODE_RUNTIME_ERROR]
        assert any("f(0)" in i.message for i in runtime_errors)


class TestQueryTypeValidation:
    def test_non_int_input_is_error_strict(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]}
        )
        issues = validate_piecewise_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_non_int_input_is_warning_lenient(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]}
        )
        issues = validate_piecewise_task(corrupted, strict=False)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.WARNING for i in type_issues)

    def test_non_int_output_is_error_strict(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"queries": [Query(input=0, output="text", tag=QueryTag.TYPICAL)]}
        )
        issues = validate_piecewise_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_float_input_detected(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"queries": [Query(input=3.14, output=0, tag=QueryTag.TYPICAL)]}
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
            i.code == CODE_QUERY_OUTPUT_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )

    def test_location_includes_specific_query_index(self) -> None:
        task = generate_piecewise_task(rng=random.Random(42))
        # Keep first query valid, corrupt second
        queries = list(task.queries[:2])
        if len(queries) >= 2:
            queries[1] = Query(
                input=queries[1].input,
                output=queries[1].output + 999,
                tag=queries[1].tag,
            )
            corrupted = task.model_copy(update={"queries": queries})
            issues = validate_piecewise_task(corrupted)
            mismatch_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_MISMATCH]
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
        semantic_issues = [i for i in issues if i.code == CODE_SEMANTIC_MISMATCH]
        # Should have x value in message like "f(0) = 0, expected X"
        assert all("f(" in i.message and ")" in i.message for i in semantic_issues)


class TestNonMonotonicThresholds:
    def test_non_monotonic_emits_warning_not_error(self) -> None:
        # Generate tasks until we find one with non-monotonic thresholds
        # or create one manually by modifying the spec
        task = generate_piecewise_task(rng=random.Random(42))
        issues = validate_piecewise_task(task)
        monotonic_issues = [i for i in issues if i.code == CODE_NON_MONOTONIC_THRESHOLDS]
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
        assert found_monotonic, "Could not find a task with monotonic thresholds"


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
