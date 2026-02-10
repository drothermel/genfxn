import random

import pytest

from genfxn.bitops import validate as bitops_validate
from genfxn.bitops.task import generate_bitops_task
from genfxn.fsm import validate as fsm_validate
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries import validate as graph_queries_validate
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals import validate as intervals_validate
from genfxn.intervals.task import generate_intervals_task
from genfxn.piecewise import validate as piecewise_validate
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp import validate as sequence_dp_validate
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms import validate as simple_validate
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stack_bytecode import validate as stack_bytecode_validate
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stateful import validate as stateful_validate
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules import validate as stringrules_validate
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.temporal_logic import validate as temporal_logic_validate
from genfxn.temporal_logic.task import generate_temporal_logic_task


def _boom(*_args, **_kwargs):
    raise AssertionError("execute_code_restricted should not run")


class _IsolatedFunc:
    def __init__(self) -> None:
        self.closed = False

    def __call__(self, *_args, **_kwargs):
        return 0

    def close(self) -> None:
        self.closed = True


def test_piecewise_validation_skips_exec_by_default(monkeypatch) -> None:
    task = generate_piecewise_task(rng=random.Random(42))
    monkeypatch.setattr(piecewise_validate, "execute_code_restricted", _boom)
    issues = piecewise_validate.validate_piecewise_task(task)
    assert not any(
        i.code == piecewise_validate.CODE_CODE_EXEC_ERROR for i in issues
    )


def test_stateful_validation_skips_exec_by_default(monkeypatch) -> None:
    task = generate_stateful_task(rng=random.Random(42))
    monkeypatch.setattr(stateful_validate, "execute_code_restricted", _boom)
    issues = stateful_validate.validate_stateful_task(task)
    assert not any(
        i.code == stateful_validate.CODE_CODE_EXEC_ERROR for i in issues
    )


def test_simple_validation_skips_exec_by_default(monkeypatch) -> None:
    task = generate_simple_algorithms_task(rng=random.Random(42))
    monkeypatch.setattr(simple_validate, "execute_code_restricted", _boom)
    issues = simple_validate.validate_simple_algorithms_task(task)
    assert not any(
        i.code == simple_validate.CODE_CODE_EXEC_ERROR for i in issues
    )


def test_stringrules_validation_skips_exec_by_default(monkeypatch) -> None:
    task = generate_stringrules_task(rng=random.Random(42))
    monkeypatch.setattr(stringrules_validate, "execute_code_restricted", _boom)
    issues = stringrules_validate.validate_stringrules_task(task)
    assert not any(
        i.code == stringrules_validate.CODE_CODE_EXEC_ERROR for i in issues
    )


def test_piecewise_validation_exec_opt_in(monkeypatch) -> None:
    task = generate_piecewise_task(rng=random.Random(42))
    monkeypatch.setattr(piecewise_validate, "execute_code_restricted", _boom)
    issues = piecewise_validate.validate_piecewise_task(
        task,
        execute_untrusted_code=True,
    )
    assert any(
        i.code == piecewise_validate.CODE_CODE_EXEC_ERROR for i in issues
    )


@pytest.mark.parametrize(
    ("generator", "validator", "module"),
    [
        (
            generate_bitops_task,
            bitops_validate.validate_bitops_task,
            bitops_validate,
        ),
        (
            generate_fsm_task,
            fsm_validate.validate_fsm_task,
            fsm_validate,
        ),
        (
            generate_graph_queries_task,
            graph_queries_validate.validate_graph_queries_task,
            graph_queries_validate,
        ),
        (
            generate_intervals_task,
            intervals_validate.validate_intervals_task,
            intervals_validate,
        ),
        (
            generate_piecewise_task,
            piecewise_validate.validate_piecewise_task,
            piecewise_validate,
        ),
        (
            generate_sequence_dp_task,
            sequence_dp_validate.validate_sequence_dp_task,
            sequence_dp_validate,
        ),
        (
            generate_stateful_task,
            stateful_validate.validate_stateful_task,
            stateful_validate,
        ),
        (
            generate_simple_algorithms_task,
            simple_validate.validate_simple_algorithms_task,
            simple_validate,
        ),
        (
            generate_stack_bytecode_task,
            stack_bytecode_validate.validate_stack_bytecode_task,
            stack_bytecode_validate,
        ),
        (
            generate_stringrules_task,
            stringrules_validate.validate_stringrules_task,
            stringrules_validate,
        ),
        (
            generate_temporal_logic_task,
            temporal_logic_validate.validate_temporal_logic_task,
            temporal_logic_validate,
        ),
    ],
    ids=[
        "bitops",
        "fsm",
        "graph_queries",
        "intervals",
        "piecewise",
        "sequence_dp",
        "stateful",
        "simple_algorithms",
        "stack_bytecode",
        "stringrules",
        "temporal_logic",
    ],
)
def test_validation_closes_exec_func(
    monkeypatch, generator, validator, module
) -> None:
    task = generator(rng=random.Random(42))
    isolated = _IsolatedFunc()
    monkeypatch.setattr(
        module,
        "execute_code_restricted",
        lambda *_args, **_kwargs: {"f": isolated},
    )
    monkeypatch.setattr(
        module,
        "_validate_semantics",
        lambda *_args, **_kwargs: [],
    )

    validator(task, execute_untrusted_code=True)

    assert isolated.closed


@pytest.mark.parametrize(
    ("generator", "validator", "module"),
    [
        (
            generate_bitops_task,
            bitops_validate.validate_bitops_task,
            bitops_validate,
        ),
        (
            generate_fsm_task,
            fsm_validate.validate_fsm_task,
            fsm_validate,
        ),
        (
            generate_graph_queries_task,
            graph_queries_validate.validate_graph_queries_task,
            graph_queries_validate,
        ),
        (
            generate_intervals_task,
            intervals_validate.validate_intervals_task,
            intervals_validate,
        ),
        (
            generate_sequence_dp_task,
            sequence_dp_validate.validate_sequence_dp_task,
            sequence_dp_validate,
        ),
        (
            generate_stack_bytecode_task,
            stack_bytecode_validate.validate_stack_bytecode_task,
            stack_bytecode_validate,
        ),
        (
            generate_temporal_logic_task,
            temporal_logic_validate.validate_temporal_logic_task,
            temporal_logic_validate,
        ),
    ],
    ids=[
        "bitops",
        "fsm",
        "graph_queries",
        "intervals",
        "sequence_dp",
        "stack_bytecode",
        "temporal_logic",
    ],
)
def test_validation_closes_exec_func_when_semantics_raises(
    monkeypatch, generator, validator, module
) -> None:
    task = generator(rng=random.Random(42))
    isolated = _IsolatedFunc()
    monkeypatch.setattr(
        module,
        "execute_code_restricted",
        lambda *_args, **_kwargs: {"f": isolated},
    )
    monkeypatch.setattr(
        module,
        "_validate_semantics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        validator(task, execute_untrusted_code=True)

    assert isolated.closed
