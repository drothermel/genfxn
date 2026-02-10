import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.predicates import PredicateGt
from genfxn.core.validate import Severity
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    SimpleAlgorithmsAxes,
    TemplateType,
)
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.simple_algorithms.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_CODE_RUNTIME_ERROR,
    CODE_COUNTING_MODE_MISMATCH,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_SPEC_DESERIALIZE_ERROR,
    CODE_TASK_ID_MISMATCH,
    CODE_UNSAFE_AST,
    _check_counting_mode_consistency,
    _validate_ast_whitelist,
    _validate_query_types,
)
from genfxn.simple_algorithms.validate import (
    validate_simple_algorithms_task as _validate_simple_algorithms_task,
)


def validate_simple_algorithms_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_simple_algorithms_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_simple_algorithms_task(rng=random.Random(42))


class TestValidTask:
    def test_generated_task_has_no_errors(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        issues = validate_simple_algorithms_task(task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    @pytest.mark.full
    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_simple_algorithms_task(rng=random.Random(seed))
            issues = validate_simple_algorithms_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"Seed {seed} produced errors: {errors}"


class TestTaskIdValidation:
    def test_corrupted_task_id_detected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"task_id": "simple_algorithms_00000000"}
        )
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)
        assert any(
            i.code == CODE_TASK_ID_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )


class TestSpecDeserialization:
    def test_invalid_spec_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"spec": {"invalid": "spec"}})
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)

    def test_wrong_template_discriminator(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"spec": {"template": "nonexistent_template"}}
        )
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)


class TestCodeCompilation:
    def test_syntax_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "def f(xs):\n    return ("})
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_exec_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "raise ValueError('boom')"})
        issues = validate_simple_algorithms_task(corrupted)
        assert any(
            i.code in {CODE_CODE_EXEC_ERROR, CODE_UNSAFE_AST} for i in issues
        )

    def test_missing_func_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "def g(xs):\n    return 0"})
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_CODE_MISSING_FUNC for i in issues)

    def test_python_code_map_validates_python_entry(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        assert isinstance(task.code, str)
        mapped = task.model_copy(
            update={
                "code": {
                    "python": task.code,
                    "java": "public static int f(int[] xs) { return 0; }",
                }
            }
        )
        issues = validate_simple_algorithms_task(mapped)
        assert not any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_non_python_code_map_skips_python_validation(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        mapped = task.model_copy(
            update={
                "code": {
                    "java": "public static int f(int[] xs) { return 0; }"
                }
            }
        )
        issues = validate_simple_algorithms_task(mapped)
        assert not any(i.code == CODE_CODE_PARSE_ERROR for i in issues)
        assert not any(i.code == CODE_CODE_EXEC_ERROR for i in issues)
        assert not any(i.code == CODE_CODE_MISSING_FUNC for i in issues)

    def test_exec_function_is_closed_after_validation(
        self,
        baseline_task: Task,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        state = {"closed": False, "calls": 0}

        def fake_fn(xs: list[int]) -> int:
            del xs
            state["calls"] += 1
            return 0

        def _close() -> None:
            state["closed"] = True

        setattr(fake_fn, "close", _close)

        def _fake_exec(*args: Any, **kwargs: Any) -> dict[str, Any]:
            del args, kwargs
            return {"f": fake_fn}

        monkeypatch.setattr(
            "genfxn.simple_algorithms.validate.execute_code_restricted",
            _fake_exec,
        )

        validate_simple_algorithms_task(
            baseline_task,
            execute_untrusted_code=True,
            max_semantic_issues=1,
            rng=random.Random(123),
        )

        assert state["calls"] >= 1
        assert state["closed"] is True


class TestCodeRuntime:
    def test_runtime_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": "def f(xs):\n    return 1 % 0"}
        )
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)


class TestQueryTypeValidation:
    def test_non_list_input_is_error_strict(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_simple_algorithms_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_non_list_input_is_warning_lenient(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [Query(input="text", output=0, tag=QueryTag.TYPICAL)]
            }
        )
        issues = validate_simple_algorithms_task(corrupted, strict=False)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.WARNING for i in type_issues)

    def test_non_int_output_is_error_strict(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, 2], output="text", tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_simple_algorithms_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.ERROR for i in type_issues)

    def test_non_int_output_is_warning_lenient(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, 2], output="text", tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_simple_algorithms_task(corrupted, strict=False)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0
        assert all(i.severity == Severity.WARNING for i in type_issues)

    def test_non_int_element_in_list_input_is_error(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[1, "two", 3], output=0, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_simple_algorithms_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0

    def test_query_type_checks_run_with_bad_spec(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "spec": {"invalid": "spec"},
                "queries": [
                    Query(
                        input=[1, "two", 3], output="bad", tag=QueryTag.TYPICAL
                    )
                ],
            }
        )
        issues = validate_simple_algorithms_task(corrupted, strict=True)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)

    def test_bool_query_values_are_rejected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=[True, 1], output=False, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)
        assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)


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

    def test_ast_whitelist_allows_annotation_names(self) -> None:
        code = "def f(xs: list[int]) -> int:\n    return 0"
        issues, _ = _validate_ast_whitelist(code)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_ast_whitelist_rejects_dunder_attribute_read(self) -> None:
        code = "def f(xs):\n    return xs.__class__"
        issues, _ = _validate_ast_whitelist(code)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)


class TestQueryOutputValidation:
    def test_wrong_output_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        first_query = task.queries[0]
        wrong_query = Query(
            input=first_query.input,
            output=first_query.output + 999,
            tag=first_query.tag,
        )
        corrupted = task.model_copy(update={"queries": [wrong_query]})
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)


class TestSemanticValidation:
    def test_code_differing_from_spec_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "def f(xs):\n    return 0"})
        issues = validate_simple_algorithms_task(corrupted)
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)

    def test_counting_mode_check_preserves_full_spec(self) -> None:
        task = generate_simple_algorithms_task(
            axes=SimpleAlgorithmsAxes(templates=[TemplateType.COUNT_PAIRS_SUM]),
            rng=random.Random(42),
        )
        query = Query(input=[1, 1, 1, -2], output=1, tag=QueryTag.TYPICAL)
        corrupted = task.model_copy(
            update={
                "queries": [query],
            }
        )
        spec = CountPairsSumSpec(
            target=2,
            counting_mode=CountingMode.ALL_INDICES,
            pre_filter=PredicateGt(value=0),
        )
        issues = _check_counting_mode_consistency(corrupted, spec)
        assert any(i.code == CODE_COUNTING_MODE_MISMATCH for i in issues)


class TestSemanticIssueCapping:
    def test_caps_semantic_mismatch_issues(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": "def f(xs):\n    return 999999"}
        )
        issues = validate_simple_algorithms_task(corrupted)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        assert len(semantic_issues) == 10
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_custom_cap_respected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "def f(xs):\n    return 0"})
        issues = validate_simple_algorithms_task(
            corrupted, max_semantic_issues=3
        )
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        assert len(semantic_issues) == 3


def _make_task_with_code(code: str) -> Task:
    task = generate_simple_algorithms_task(rng=random.Random(42))
    return task.model_copy(update={"code": code})


@pytest.mark.slow
class TestParanoidMode:
    def test_valid_generated_code_passes(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        issues = validate_simple_algorithms_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_import_rejected(self) -> None:
        task = _make_task_with_code("import os\ndef f(xs): return 0")
        issues = validate_simple_algorithms_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert len(unsafe) >= 1

    def test_method_arity_mismatch_rejected(self) -> None:
        task = _make_task_with_code("def f(xs): return {}.get(1, 2, 3)")
        issues = validate_simple_algorithms_task(task, paranoid=True)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_unsafe_code_rejected_without_paranoid_flag(self) -> None:
        task = _make_task_with_code("import os\ndef f(xs): return 0")
        issues = validate_simple_algorithms_task(task, paranoid=False)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    @pytest.mark.full
    def test_multiple_seeds_pass_paranoid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_simple_algorithms_task(rng=random.Random(seed))
            issues = validate_simple_algorithms_task(task, paranoid=True)
            assert not any(i.code == CODE_UNSAFE_AST for i in issues), (
                f"Seed {seed} produced UNSAFE_AST issues"
            )


class TestEachTemplate:
    def test_most_frequent_valid(self) -> None:
        axes = SimpleAlgorithmsAxes(templates=[TemplateType.MOST_FREQUENT])
        task = generate_simple_algorithms_task(axes=axes, rng=random.Random(42))
        issues = validate_simple_algorithms_task(task, axes=axes, paranoid=True)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == [], f"Errors: {errors}"

    def test_count_pairs_sum_valid(self) -> None:
        axes = SimpleAlgorithmsAxes(templates=[TemplateType.COUNT_PAIRS_SUM])
        task = generate_simple_algorithms_task(axes=axes, rng=random.Random(42))
        issues = validate_simple_algorithms_task(task, axes=axes, paranoid=True)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == [], f"Errors: {errors}"

    def test_max_window_sum_valid(self) -> None:
        axes = SimpleAlgorithmsAxes(templates=[TemplateType.MAX_WINDOW_SUM])
        task = generate_simple_algorithms_task(axes=axes, rng=random.Random(42))
        issues = validate_simple_algorithms_task(task, axes=axes, paranoid=True)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == [], f"Errors: {errors}"
