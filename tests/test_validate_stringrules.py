import random

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Severity
from genfxn.stringrules.models import OverlapLevel, StringRulesAxes
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.stringrules.validate import (
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
    DEFAULT_MAX_SEMANTIC_ISSUES,
    validate_stringrules_task,
)


class TestValidTask:
    def test_generated_task_has_no_errors(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        issues = validate_stringrules_task(task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_stringrules_task(rng=random.Random(seed))
            issues = validate_stringrules_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"Seed {seed} produced errors: {errors}"


class TestTaskIdValidation:
    def test_corrupted_task_id_detected(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"task_id": "stringrules_00000000"})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)
        assert any(
            i.code == CODE_TASK_ID_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )


class TestSpecDeserialization:
    def test_invalid_spec_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"spec": {"invalid": "spec"}})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)

    def test_missing_rules(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"spec": {"default_transform": {"kind": "identity"}}}
        )
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)


class TestCodeCompilation:
    def test_syntax_error_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(s):\n    return ("})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_exec_error_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "raise ValueError('boom')"})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_EXEC_ERROR for i in issues)

    def test_missing_func_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def g(s):\n    return s"})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_MISSING_FUNC for i in issues)


class TestCodeRuntime:
    def test_runtime_error_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"code": "def f(s):\n    raise ZeroDivisionError('oops')"}
        )
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)


class TestQueryTypeValidation:
    def test_non_str_input_is_error_strict(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"queries": [Query(input=123, output="abc", tag=QueryTag.TYPICAL)]}
        )
        issues = validate_stringrules_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0

    def test_non_str_output_is_error_strict(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(
            update={"queries": [Query(input="hello", output=123, tag=QueryTag.TYPICAL)]}
        )
        issues = validate_stringrules_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0


class TestQueryOutputValidation:
    def test_wrong_output_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        first_query = task.queries[0]
        wrong_query = Query(
            input=first_query.input,
            output=first_query.output + "_WRONG",
            tag=first_query.tag,
        )
        corrupted = task.model_copy(update={"queries": [wrong_query]})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)


class TestSemanticValidation:
    def test_code_differing_from_spec_caught(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(s):\n    return 'wrong'"})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)


class TestSemanticIssueCapping:
    def test_caps_semantic_mismatch_issues(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(s):\n    return 'WRONG'"})
        issues = validate_stringrules_task(corrupted)
        semantic_issues = [i for i in issues if i.code == CODE_SEMANTIC_MISMATCH]
        assert len(semantic_issues) == DEFAULT_MAX_SEMANTIC_ISSUES
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_custom_cap_respected(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        corrupted = task.model_copy(update={"code": "def f(s):\n    return 'wrong'"})
        issues = validate_stringrules_task(corrupted, max_semantic_issues=3)
        semantic_issues = [i for i in issues if i.code == CODE_SEMANTIC_MISMATCH]
        assert len(semantic_issues) == 3


def _make_task_with_code(code: str) -> Task:
    task = generate_stringrules_task(rng=random.Random(42))
    return task.model_copy(update={"code": code})


class TestParanoidMode:
    def test_valid_generated_code_passes(self) -> None:
        task = generate_stringrules_task(rng=random.Random(42))
        issues = validate_stringrules_task(task, paranoid=True)
        assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_import_rejected(self) -> None:
        task = _make_task_with_code("import os\ndef f(s): return s")
        issues = validate_stringrules_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert len(unsafe) >= 1

    def test_method_arity_mismatch_rejected(self) -> None:
        # replace() requires 2 or 3 args; 1 arg is invalid
        task = _make_task_with_code('def f(s): return s.replace("a")')
        issues = validate_stringrules_task(task, paranoid=True)
        unsafe = [i for i in issues if i.code == CODE_UNSAFE_AST]
        assert len(unsafe) >= 1
        assert any(
            "replace" in i.message and "argument" in i.message.lower()
            for i in unsafe
        )

    def test_multiple_seeds_pass_paranoid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_stringrules_task(rng=random.Random(seed))
            issues = validate_stringrules_task(task, paranoid=True)
            assert not any(i.code == CODE_UNSAFE_AST for i in issues), (
                f"Seed {seed} produced UNSAFE_AST issues"
            )


class TestDifferentConfigurations:
    def test_different_n_rules(self) -> None:
        for n in [1, 2, 4]:
            axes = StringRulesAxes(n_rules=n)
            task = generate_stringrules_task(axes=axes, rng=random.Random(42))
            issues = validate_stringrules_task(task, axes=axes, paranoid=True)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"n_rules={n}: {errors}"

    def test_different_overlap_levels(self) -> None:
        for overlap in OverlapLevel:
            axes = StringRulesAxes(n_rules=3, overlap_level=overlap)
            task = generate_stringrules_task(axes=axes, rng=random.Random(42))
            issues = validate_stringrules_task(task, axes=axes, paranoid=True)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"overlap={overlap}: {errors}"
