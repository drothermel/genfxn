import random

import pytest

from genfxn.piecewise import validate as piecewise_validate
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.simple_algorithms import validate as simple_validate
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stateful import validate as stateful_validate
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules import validate as stringrules_validate
from genfxn.stringrules.task import generate_stringrules_task


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
            generate_piecewise_task,
            piecewise_validate.validate_piecewise_task,
            piecewise_validate,
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
            generate_stringrules_task,
            stringrules_validate.validate_stringrules_task,
            stringrules_validate,
        ),
    ],
    ids=["piecewise", "stateful", "simple_algorithms", "stringrules"],
)
def test_validation_closes_exec_func_when_spec_is_invalid(
    monkeypatch, generator, validator, module
) -> None:
    task = generator(rng=random.Random(42)).model_copy(
        update={"spec": {"invalid": "spec"}}
    )
    isolated = _IsolatedFunc()
    monkeypatch.setattr(
        module,
        "execute_code_restricted",
        lambda *_args, **_kwargs: {"f": isolated},
    )

    validator(task, execute_untrusted_code=True)

    assert isolated.closed
