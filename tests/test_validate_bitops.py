import random
from typing import Any

import pytest

from genfxn.bitops.eval import eval_bitops
from genfxn.bitops.models import BitopsAxes, BitopsSpec
from genfxn.bitops.task import generate_bitops_task
from genfxn.bitops.validate import (
    CODE_CODE_EXEC_ERROR,
    CODE_QUERY_INPUT_TYPE,
    CODE_QUERY_OUTPUT_MISMATCH,
    CODE_QUERY_OUTPUT_TYPE,
    CODE_SEMANTIC_MISMATCH,
    CODE_UNSAFE_AST,
)
from genfxn.bitops.validate import validate_bitops_task as _validate_bitops_task
from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.validate import Severity


def validate_bitops_task(*args: Any, **kwargs: Any):
    kwargs.setdefault("execute_untrusted_code", True)
    return _validate_bitops_task(*args, **kwargs)


@pytest.fixture
def baseline_task() -> Task:
    return generate_bitops_task(rng=random.Random(42))


def test_generated_task_has_no_errors(baseline_task: Task) -> None:
    issues = validate_bitops_task(baseline_task)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    assert errors == []


def test_unsafe_ast_is_rejected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={"code": "def f(x):\n    import os\n    return x"}
    )
    issues = validate_bitops_task(corrupted)
    assert any(i.code == CODE_UNSAFE_AST for i in issues)


def test_query_type_mismatch_detected(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(
        update={
            "queries": [
                Query(input="bad", output="bad", tag=QueryTag.TYPICAL)
            ]
        }
    )
    issues = validate_bitops_task(corrupted)
    assert any(i.code == CODE_QUERY_INPUT_TYPE for i in issues)
    assert any(i.code == CODE_QUERY_OUTPUT_TYPE for i in issues)


def test_query_output_mismatch_detected(baseline_task: Task) -> None:
    query = baseline_task.queries[0]
    bad_query = Query(
        input=query.input,
        output=query.output + 1,
        tag=query.tag,
    )
    corrupted = baseline_task.model_copy(update={"queries": [bad_query]})
    issues = validate_bitops_task(corrupted)
    assert any(i.code == CODE_QUERY_OUTPUT_MISMATCH for i in issues)


def test_semantic_mismatch_detected(baseline_task: Task) -> None:
    spec = BitopsSpec.model_validate(baseline_task.spec, strict=True)
    expected = eval_bitops(spec, 1)
    corrupted = baseline_task.model_copy(
        update={"code": f"def f(x):\n    return {expected + 1}"}
    )
    issues = validate_bitops_task(
        corrupted,
        axes=BitopsAxes(value_range=(1, 1)),
        semantic_trials=4,
        max_semantic_issues=4,
        random_seed=123,
    )
    assert any(i.code == CODE_SEMANTIC_MISMATCH for i in issues)


def test_execute_untrusted_code_false_skips_exec(baseline_task: Task) -> None:
    corrupted = baseline_task.model_copy(update={"code": "raise ValueError(1)"})
    issues = _validate_bitops_task(corrupted, execute_untrusted_code=False)
    assert not any(i.code == CODE_CODE_EXEC_ERROR for i in issues)


def test_execute_untrusted_code_true_reports_exec_error(
    baseline_task: Task,
) -> None:
    corrupted = baseline_task.model_copy(update={"code": "raise ValueError(1)"})
    issues = _validate_bitops_task(corrupted, execute_untrusted_code=True)
    assert any(i.code == CODE_CODE_EXEC_ERROR for i in issues)
