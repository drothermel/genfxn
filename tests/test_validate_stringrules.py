import random
from typing import Any

import pytest

from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.string_predicates import (
    StringPredicateStartsWith,
)
from genfxn.core.string_transforms import (
    StringTransformIdentity,
    StringTransformLowercase,
    StringTransformUppercase,
)
from genfxn.core.validate import Severity
from genfxn.stringrules.models import (
    OverlapLevel,
    StringRule,
    StringRulesAxes,
    StringRulesSpec,
)
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.stringrules.validate import (
    CODE_AXES_INVALID,
    CODE_CODE_EXEC_ERROR,
    CODE_CODE_MISSING_FUNC,
    CODE_CODE_PARSE_ERROR,
    CODE_CODE_RUNTIME_ERROR,
    CODE_EMPTY_RULESET,
    CODE_INVALID_CHARSET,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_ISSUES_CAPPED,
    CODE_SEMANTIC_MISMATCH,
    CODE_SHADOWED_RULE,
    CODE_SPEC_DESERIALIZE_ERROR,
    CODE_TASK_ID_MISMATCH,
    CODE_UNSAFE_AST,
    DEFAULT_MAX_SEMANTIC_ISSUES,
    _generate_test_inputs,
    _validate_ast_whitelist,
    _validate_query_types,
    _validate_rule_diagnostics,
)
from genfxn.stringrules.validate import (
    validate_stringrules_task as _validate_stringrules_task,
)


def validate_stringrules_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_stringrules_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_stringrules_task(rng=random.Random(42))


class TestValidTask:
    def test_generated_task_has_no_errors(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        issues = validate_stringrules_task(task)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert errors == []

    @pytest.mark.full
    def test_multiple_seeds_valid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_stringrules_task(rng=random.Random(seed))
            issues = validate_stringrules_task(task)
            errors = [i for i in issues if i.severity == Severity.ERROR]
            assert errors == [], f"Seed {seed} produced errors: {errors}"


class TestTaskIdValidation:
    def test_corrupted_task_id_detected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"task_id": "stringrules_00000000"})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_TASK_ID_MISMATCH for i in issues)
        assert any(
            i.code == CODE_TASK_ID_MISMATCH and i.severity == Severity.ERROR
            for i in issues
        )


class TestSpecDeserialization:
    def test_invalid_spec_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"spec": {"invalid": "spec"}})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)

    def test_missing_rules(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"spec": {"default_transform": {"kind": "identity"}}}
        )
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_SPEC_DESERIALIZE_ERROR for i in issues)


class TestCodeCompilation:
    def test_syntax_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "def f(s):\n    return ("})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_PARSE_ERROR for i in issues)

    def test_exec_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "raise ValueError('boom')"})
        issues = validate_stringrules_task(corrupted)
        assert any(
            i.code in {CODE_CODE_EXEC_ERROR, CODE_UNSAFE_AST} for i in issues
        )

    def test_missing_func_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(update={"code": "def g(s):\n    return s"})
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_MISSING_FUNC for i in issues)


class TestCodeRuntime:
    def test_runtime_error_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": "def f(s):\n    return s[1000]"}
        )
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_CODE_RUNTIME_ERROR for i in issues)


class TestQueryTypeValidation:
    def test_non_str_input_is_error_strict(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input=123, output="abc", tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_stringrules_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_INPUT_TYPE]
        assert len(type_issues) > 0

    def test_non_str_output_is_error_strict(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={
                "queries": [
                    Query(input="hello", output=123, tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = validate_stringrules_task(corrupted, strict=True)
        type_issues = [i for i in issues if i.code == CODE_QUERY_OUTPUT_TYPE]
        assert len(type_issues) > 0


class TestHelperLevelValidation:
    def test_query_types_helper_without_full_pipeline(
        self, baseline_task
    ) -> None:
        corrupted = baseline_task.model_copy(
            update={
                "queries": [
                    Query(input=123, output="abc", tag=QueryTag.TYPICAL)
                ]
            }
        )
        issues = _validate_query_types(corrupted, strict=True)
        assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)

    def test_ast_whitelist_helper_without_execution(self) -> None:
        issues, _ = _validate_ast_whitelist("import os\ndef f(s): return s")
        assert any(i.code == CODE_UNSAFE_AST for i in issues)


class TestQueryOutputValidation:
    def test_wrong_output_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
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
    def test_code_differing_from_spec_caught(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": "def f(s):\n    return 'wrong'"}
        )
        issues = validate_stringrules_task(corrupted)
        assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)


class TestSemanticIssueCapping:
    def test_caps_semantic_mismatch_issues(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": "def f(s):\n    return 'WRONG'"}
        )
        issues = validate_stringrules_task(corrupted)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        assert len(semantic_issues) == DEFAULT_MAX_SEMANTIC_ISSUES
        assert any(i.code == CODE_SEMANTIC_ISSUES_CAPPED for i in issues)

    def test_custom_cap_respected(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
        corrupted = task.model_copy(
            update={"code": "def f(s):\n    return 'wrong'"}
        )
        issues = validate_stringrules_task(corrupted, max_semantic_issues=3)
        semantic_issues = [
            i for i in issues if i.code == CODE_SEMANTIC_MISMATCH
        ]
        assert len(semantic_issues) == 3


def _make_task_with_code(code: str) -> Task:
    task = generate_stringrules_task(rng=random.Random(42))
    return task.model_copy(update={"code": code})


@pytest.mark.slow
class TestParanoidMode:
    def test_valid_generated_code_passes(self, baseline_task) -> None:
        task = baseline_task.model_copy(deep=True)
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

    def test_unsafe_code_rejected_without_paranoid_flag(self) -> None:
        task = _make_task_with_code("import os\ndef f(s): return s")
        issues = validate_stringrules_task(task, paranoid=False)
        assert any(i.code == CODE_UNSAFE_AST for i in issues)

    @pytest.mark.full
    def test_multiple_seeds_pass_paranoid(self) -> None:
        for seed in [1, 42, 123, 999]:
            task = generate_stringrules_task(rng=random.Random(seed))
            issues = validate_stringrules_task(task, paranoid=True)
            assert not any(i.code == CODE_UNSAFE_AST for i in issues), (
                f"Seed {seed} produced UNSAFE_AST issues"
            )


@pytest.mark.full
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

    def test_generate_test_inputs_respects_digits_charset(self) -> None:
        axes = StringRulesAxes(charset="digits", string_length_range=(1, 5))
        inputs = _generate_test_inputs(axes, random.Random(42), num_samples=30)
        assert inputs
        assert all(all(ch.isdigit() for ch in s) for s in inputs)

    def test_generate_test_inputs_space_charset_avoids_invalid_literal(
        self,
    ) -> None:
        axes = StringRulesAxes(charset=" ", string_length_range=(1, 10))
        inputs = _generate_test_inputs(axes, random.Random(42), num_samples=30)
        assert inputs
        assert all(set(s) <= {" "} for s in inputs)
        assert " " * 10 in inputs
        assert "  spaces  " not in inputs

    def test_empty_charset_axes_returns_issue_not_exception(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        issues = validate_stringrules_task(task, axes={"charset": ""})
        assert any(i.code == CODE_AXES_INVALID for i in issues)
        assert any(
            i.code == CODE_AXES_INVALID and i.location == "axes.charset"
            for i in issues
        )


class TestDiagnostics:
    def test_empty_ruleset_emits_diagnostic(self, baseline_task) -> None:
        task = baseline_task.model_copy(
            update={
                "spec": StringRulesSpec(
                    rules=[],
                    default_transform=StringTransformIdentity(),
                ).model_dump()
            }
        )
        issues = validate_stringrules_task(task, emit_diagnostics=True)
        assert any(i.code == CODE_EMPTY_RULESET for i in issues)

    def test_shadowed_rule_emits_diagnostic(self, baseline_task) -> None:
        task = baseline_task.model_copy(
            update={
                "spec": StringRulesSpec(
                    rules=[
                        StringRule(
                            predicate=StringPredicateStartsWith(prefix="a"),
                            transform=StringTransformUppercase(),
                        ),
                        StringRule(
                            predicate=StringPredicateStartsWith(prefix="a"),
                            transform=StringTransformLowercase(),
                        ),
                    ],
                    default_transform=StringTransformIdentity(),
                ).model_dump()
            }
        )
        issues = validate_stringrules_task(task, emit_diagnostics=True)
        assert any(
            i.code == CODE_SHADOWED_RULE and i.location == "spec.rules[1]"
            for i in issues
        )

    def test_shadowed_rule_diagnostic_can_be_disabled(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(
            update={
                "spec": StringRulesSpec(
                    rules=[
                        StringRule(
                            predicate=StringPredicateStartsWith(prefix="a"),
                            transform=StringTransformUppercase(),
                        ),
                        StringRule(
                            predicate=StringPredicateStartsWith(prefix="a"),
                            transform=StringTransformLowercase(),
                        ),
                    ],
                    default_transform=StringTransformIdentity(),
                ).model_dump()
            }
        )
        issues = validate_stringrules_task(task, emit_diagnostics=False)
        assert not any(i.code == CODE_SHADOWED_RULE for i in issues)

    def test_rule_diagnostics_invalid_charset_returns_issue(
        self, baseline_task
    ) -> None:
        task = baseline_task.model_copy(deep=True)
        spec = StringRulesSpec.model_validate(task.spec)
        axes = StringRulesAxes.model_construct(  # bypass validation
            charset="",
            string_length_range=(0, 20),
            n_rules=2,
            overlap_level=OverlapLevel.HIGH,
        )

        issues = _validate_rule_diagnostics(task, spec, axes, random.Random(42))
        assert any(
            i.code == CODE_INVALID_CHARSET
            and i.severity == Severity.ERROR
            and i.location == "spec.axes"
            and i.task_id == task.task_id
            for i in issues
        )
