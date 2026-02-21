from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from genfxn.bitops import task as bitops_task
from genfxn.bitops import validate as bitops_validate
from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Issue, Severity
from genfxn.fsm import task as fsm_task
from genfxn.fsm import validate as fsm_validate
from genfxn.graph_queries import task as graph_queries_task
from genfxn.graph_queries import validate as graph_queries_validate
from genfxn.intervals import task as intervals_task
from genfxn.intervals import validate as intervals_validate
from genfxn.piecewise import task as piecewise_task
from genfxn.piecewise import validate as piecewise_validate
from genfxn.sequence_dp import task as sequence_dp_task
from genfxn.sequence_dp import validate as sequence_dp_validate
from genfxn.simple_algorithms import task as simple_algorithms_task
from genfxn.simple_algorithms import validate as simple_algorithms_validate
from genfxn.stack_bytecode import task as stack_bytecode_task
from genfxn.stack_bytecode import validate as stack_bytecode_validate
from genfxn.stateful import task as stateful_task
from genfxn.stateful import validate as stateful_validate
from genfxn.temporal_logic import task as temporal_logic_task
from genfxn.temporal_logic import validate as temporal_logic_validate
from genfxn.temporal_logic.models import TemporalLogicAxes

GenerateTaskFn = Callable[..., Task]
ValidateTaskFn = Callable[..., list[Issue]]
QueryBuilder = Callable[[Task], Query]
KwargsFactory = Callable[[], dict[str, Any]]


def _no_kwargs() -> dict[str, Any]:
    return {}


def _sampled_lifecycle_kwargs() -> dict[str, Any]:
    return {
        "semantic_trials": 1,
        "max_semantic_issues": 1,
        "random_seed": 7,
    }


def _piecewise_lifecycle_kwargs() -> dict[str, Any]:
    return {"value_range": (0, 0), "max_semantic_issues": 1}


def _stateful_lifecycle_kwargs() -> dict[str, Any]:
    return {"max_semantic_issues": 1, "rng": random.Random(7)}


def _simple_algorithms_lifecycle_kwargs() -> dict[str, Any]:
    return {"max_semantic_issues": 1, "rng": random.Random(7)}


def _temporal_task_kwargs() -> dict[str, Any]:
    axes = TemporalLogicAxes(
        formula_depth_range=(2, 3),
        sequence_length_range=(0, 4),
        value_range=(-3, 3),
        predicate_constant_range=(-2, 2),
    )
    return {"axes": axes}


def _strictness_query(_task: Task) -> Query:
    return Query(input="bad", output="bad", tag=QueryTag.TYPICAL)


def _bool_scalar_query(_task: Task) -> Query:
    return Query(input=True, output=False, tag=QueryTag.TYPICAL)


def _bool_list_query(_task: Task) -> Query:
    return Query(input=[True, 1], output=False, tag=QueryTag.TYPICAL)


def _bool_intervals_query(_task: Task) -> Query:
    return Query(input=[(True, 1)], output=False, tag=QueryTag.TYPICAL)


def _bool_sequence_dp_query(_task: Task) -> Query:
    return Query(
        input={"a": [True, 1], "b": [0]},
        output=False,
        tag=QueryTag.TYPICAL,
    )


def _bool_graph_queries_query(_task: Task) -> Query:
    return Query(
        input={"src": True, "dst": 1},
        output=False,
        tag=QueryTag.TYPICAL,
    )


def _bool_stack_bytecode_query(_task: Task) -> Query:
    return Query(
        input=[True, 1],
        output=(True, 0),
        tag=QueryTag.TYPICAL,
    )


@dataclass(frozen=True)
class ValidatorContractCase:
    name: str
    generate_task: GenerateTaskFn
    validate_task: ValidateTaskFn
    query_input_type_code: str
    query_output_type_code: str
    code_parse_error_code: str
    code_exec_error_code: str
    code_missing_func_code: str
    code_unsafe_ast_code: str
    strictness_query: QueryBuilder
    bool_query: QueryBuilder
    task_kwargs: KwargsFactory = _no_kwargs
    lifecycle_kwargs: KwargsFactory = _no_kwargs

    @property
    def exec_patch_target(self) -> str:
        return f"{self.validate_task.__module__}.execute_code_restricted"


VALIDATOR_CASES: tuple[ValidatorContractCase, ...] = (
    ValidatorContractCase(
        name="bitops",
        generate_task=bitops_task.generate_bitops_task,
        validate_task=bitops_validate.validate_bitops_task,
        query_input_type_code=bitops_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=bitops_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=bitops_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=bitops_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=bitops_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=bitops_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_scalar_query,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="fsm",
        generate_task=fsm_task.generate_fsm_task,
        validate_task=fsm_validate.validate_fsm_task,
        query_input_type_code=fsm_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=fsm_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=fsm_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=fsm_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=fsm_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=fsm_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_list_query,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="graph_queries",
        generate_task=graph_queries_task.generate_graph_queries_task,
        validate_task=graph_queries_validate.validate_graph_queries_task,
        query_input_type_code=graph_queries_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=graph_queries_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=graph_queries_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=graph_queries_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=graph_queries_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=graph_queries_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_graph_queries_query,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="intervals",
        generate_task=intervals_task.generate_intervals_task,
        validate_task=intervals_validate.validate_intervals_task,
        query_input_type_code=intervals_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=intervals_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=intervals_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=intervals_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=intervals_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=intervals_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_intervals_query,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="piecewise",
        generate_task=piecewise_task.generate_piecewise_task,
        validate_task=piecewise_validate.validate_piecewise_task,
        query_input_type_code=piecewise_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=piecewise_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=piecewise_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=piecewise_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=piecewise_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=piecewise_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_scalar_query,
        lifecycle_kwargs=_piecewise_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="sequence_dp",
        generate_task=sequence_dp_task.generate_sequence_dp_task,
        validate_task=sequence_dp_validate.validate_sequence_dp_task,
        query_input_type_code=sequence_dp_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=sequence_dp_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=sequence_dp_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=sequence_dp_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=sequence_dp_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=sequence_dp_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_sequence_dp_query,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="simple_algorithms",
        generate_task=simple_algorithms_task.generate_simple_algorithms_task,
        validate_task=(
            simple_algorithms_validate.validate_simple_algorithms_task
        ),
        query_input_type_code=simple_algorithms_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=(
            simple_algorithms_validate.CODE_QUERY_OUTPUT_TYPE
        ),
        code_parse_error_code=(
            simple_algorithms_validate.CODE_CODE_PARSE_ERROR
        ),
        code_exec_error_code=simple_algorithms_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=(
            simple_algorithms_validate.CODE_CODE_MISSING_FUNC
        ),
        code_unsafe_ast_code=simple_algorithms_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_list_query,
        lifecycle_kwargs=_simple_algorithms_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="stack_bytecode",
        generate_task=stack_bytecode_task.generate_stack_bytecode_task,
        validate_task=stack_bytecode_validate.validate_stack_bytecode_task,
        query_input_type_code=stack_bytecode_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=stack_bytecode_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=stack_bytecode_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=stack_bytecode_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=stack_bytecode_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=stack_bytecode_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_stack_bytecode_query,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="stateful",
        generate_task=stateful_task.generate_stateful_task,
        validate_task=stateful_validate.validate_stateful_task,
        query_input_type_code=stateful_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=stateful_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=stateful_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=stateful_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=stateful_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=stateful_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_list_query,
        lifecycle_kwargs=_stateful_lifecycle_kwargs,
    ),
    ValidatorContractCase(
        name="temporal_logic",
        generate_task=temporal_logic_task.generate_temporal_logic_task,
        validate_task=temporal_logic_validate.validate_temporal_logic_task,
        query_input_type_code=temporal_logic_validate.CODE_QUERY_INPUT_TYPE,
        query_output_type_code=temporal_logic_validate.CODE_QUERY_OUTPUT_TYPE,
        code_parse_error_code=temporal_logic_validate.CODE_CODE_PARSE_ERROR,
        code_exec_error_code=temporal_logic_validate.CODE_CODE_EXEC_ERROR,
        code_missing_func_code=temporal_logic_validate.CODE_CODE_MISSING_FUNC,
        code_unsafe_ast_code=temporal_logic_validate.CODE_UNSAFE_AST,
        strictness_query=_strictness_query,
        bool_query=_bool_list_query,
        task_kwargs=_temporal_task_kwargs,
        lifecycle_kwargs=_sampled_lifecycle_kwargs,
    ),
)


def _baseline_task(case: ValidatorContractCase) -> Task:
    return case.generate_task(
        rng=random.Random(42),
        **case.task_kwargs(),
    )


def _f_signature(case_name: str) -> str:
    signature_by_case = {
        "bitops": "x",
        "fsm": "xs",
        "graph_queries": "src, dst",
        "intervals": "intervals",
        "piecewise": "x",
        "sequence_dp": "a, b",
        "simple_algorithms": "xs",
        "stack_bytecode": "xs",
        "stateful": "xs",
        "temporal_logic": "xs",
    }
    return signature_by_case[case_name]


def _top_level_side_effect_code(case_name: str) -> str:
    return f"sentinel = 1\ndef f({_f_signature(case_name)}):\n    return 0"


def _non_call_attribute_code(case_name: str) -> str:
    return f"def f({_f_signature(case_name)}):\n    return (1).real"


def _query_type_issues(
    issues: list[Issue], case: ValidatorContractCase
) -> list[Issue]:
    target_codes = {
        case.query_input_type_code,
        case.query_output_type_code,
    }
    return [issue for issue in issues if issue.code in target_codes]


@pytest.mark.parametrize(
    "case",
    VALIDATOR_CASES,
    ids=[case.name for case in VALIDATOR_CASES],
)
def test_strict_vs_lenient_query_type_severity(
    case: ValidatorContractCase,
) -> None:
    task = _baseline_task(case)
    corrupted = task.model_copy(
        update={"queries": [case.strictness_query(task)]}
    )

    strict_issues = case.validate_task(
        corrupted,
        strict=True,
        execute_untrusted_code=False,
    )
    lenient_issues = case.validate_task(
        corrupted,
        strict=False,
        execute_untrusted_code=False,
    )

    strict_type_issues = _query_type_issues(strict_issues, case)
    lenient_type_issues = _query_type_issues(lenient_issues, case)
    assert strict_type_issues
    assert lenient_type_issues
    assert all(issue.severity == Severity.ERROR for issue in strict_type_issues)
    assert all(
        issue.severity == Severity.WARNING for issue in lenient_type_issues
    )


@pytest.mark.parametrize(
    "case",
    VALIDATOR_CASES,
    ids=[case.name for case in VALIDATOR_CASES],
)
def test_bool_values_rejected_for_int_like_query_fields(
    case: ValidatorContractCase,
) -> None:
    task = _baseline_task(case)
    corrupted = task.model_copy(update={"queries": [case.bool_query(task)]})

    issues = case.validate_task(
        corrupted,
        strict=True,
        execute_untrusted_code=False,
    )
    codes = {issue.code for issue in issues}
    assert case.query_input_type_code in codes
    assert case.query_output_type_code in codes


@pytest.mark.parametrize(
    "case",
    VALIDATOR_CASES,
    ids=[case.name for case in VALIDATOR_CASES],
)
def test_non_python_code_map_skips_python_validation_path(
    case: ValidatorContractCase,
) -> None:
    task = _baseline_task(case)
    java_only = task.model_copy(
        update={"code": {"java": "public class Solution {}"}}
    )

    issues = case.validate_task(
        java_only,
        strict=True,
        execute_untrusted_code=True,
    )
    blocked_codes = {
        case.code_parse_error_code,
        case.code_exec_error_code,
        case.code_missing_func_code,
    }
    assert not any(issue.code in blocked_codes for issue in issues)


@pytest.mark.parametrize(
    "case",
    VALIDATOR_CASES,
    ids=[case.name for case in VALIDATOR_CASES],
)
def test_exec_function_close_lifecycle_contract(
    case: ValidatorContractCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"closed": False, "calls": 0}

    def fake_fn(*args: Any, **kwargs: Any) -> int:
        del args, kwargs
        state["calls"] += 1
        return 0

    def _close() -> None:
        state["closed"] = True

    setattr(fake_fn, "close", _close)

    def _stub_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        del args, kwargs
        return {"f": fake_fn}

    monkeypatch.setattr(case.exec_patch_target, _stub_execute)

    task = _baseline_task(case)
    case.validate_task(
        task,
        execute_untrusted_code=True,
        **case.lifecycle_kwargs(),
    )

    assert state["calls"] >= 1
    assert state["closed"] is True


@pytest.mark.parametrize(
    "case",
    VALIDATOR_CASES,
    ids=[case.name for case in VALIDATOR_CASES],
)
def test_top_level_side_effects_rejected_by_ast_contract(
    case: ValidatorContractCase,
) -> None:
    task = _baseline_task(case)
    corrupted = task.model_copy(
        update={"code": _top_level_side_effect_code(case.name)}
    )

    issues = case.validate_task(
        corrupted,
        strict=True,
        execute_untrusted_code=False,
    )
    codes = {issue.code for issue in issues}
    assert case.code_unsafe_ast_code in codes


@pytest.mark.parametrize(
    "case",
    VALIDATOR_CASES,
    ids=[case.name for case in VALIDATOR_CASES],
)
def test_non_call_attributes_rejected_by_ast_contract(
    case: ValidatorContractCase,
) -> None:
    task = _baseline_task(case)
    corrupted = task.model_copy(
        update={"code": _non_call_attribute_code(case.name)}
    )

    issues = case.validate_task(
        corrupted,
        strict=True,
        execute_untrusted_code=False,
    )
    codes = {issue.code for issue in issues}
    assert case.code_unsafe_ast_code in codes
