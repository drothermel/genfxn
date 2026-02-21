from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import typer
from helpers import load_script_module

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_generated_code_quality.py"
)

_SCRIPT_MODULE = load_script_module(
    _SCRIPT, "tests.check_generated_code_quality_script_module"
)
check_generated_code_quality_main = cast(
    Callable[..., None], _SCRIPT_MODULE.main
)


class _FakeTask:
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id


class _FakeCandidate:
    def __init__(self, task: _FakeTask) -> None:
        self.task = task


def test_main_samples_tasks_and_runs_checks(monkeypatch) -> None:
    pool_calls: list[tuple[str, int, int]] = []
    checked_task_ids: list[str] = []

    def _fake_generate_pool(
        family: str, seed: int, pool_size: int
    ) -> tuple[list[_FakeCandidate], SimpleNamespace]:
        pool_calls.append((family, seed, pool_size))
        candidates = [
            _FakeCandidate(_FakeTask(f"{family}-0")),
            _FakeCandidate(_FakeTask(f"{family}-1")),
            _FakeCandidate(_FakeTask(f"{family}-2")),
        ]
        return candidates, SimpleNamespace(errors=0, duplicates=0)

    def _fake_check(tasks: list[_FakeTask]) -> None:
        checked_task_ids.extend(task.task_id for task in tasks)

    monkeypatch.setattr(_SCRIPT_MODULE, "generate_pool", _fake_generate_pool)
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        _fake_check,
    )

    check_generated_code_quality_main(
        families="piecewise,stateful",
        seed=9,
        count_per_family=2,
        pool_size=5,
    )

    assert pool_calls == [
        ("piecewise", 9, 5),
        ("stateful", 10_009, 5),
    ]
    assert checked_task_ids == [
        "piecewise-0",
        "piecewise-1",
        "stateful-0",
        "stateful-1",
    ]


def test_main_raises_for_insufficient_candidates(monkeypatch) -> None:
    def _fake_generate_pool(
        family: str,
        seed: int,
        pool_size: int,  # noqa: ARG001
    ) -> tuple[list[_FakeCandidate], SimpleNamespace]:
        return [_FakeCandidate(_FakeTask(f"{family}-0"))], SimpleNamespace(
            errors=2, duplicates=3
        )

    monkeypatch.setattr(_SCRIPT_MODULE, "generate_pool", _fake_generate_pool)
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        lambda tasks: None,
    )

    with pytest.raises(typer.BadParameter, match="produced only 1"):
        check_generated_code_quality_main(
            families="piecewise",
            seed=7,
            count_per_family=2,
            pool_size=4,
        )


def test_main_exits_when_quality_checks_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_pool",
        lambda family, seed, pool_size: (  # noqa: ARG005
            [
                _FakeCandidate(_FakeTask("t0")),
                _FakeCandidate(_FakeTask("t1")),
            ],
            SimpleNamespace(errors=0, duplicates=0),
        ),
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        lambda tasks: (_ for _ in ()).throw(
            _SCRIPT_MODULE.GeneratedCodeQualityError("quality failure")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        check_generated_code_quality_main(
            families="piecewise",
            seed=7,
            count_per_family=2,
            pool_size=4,
        )

    assert exc_info.value.exit_code == 1
