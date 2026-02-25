from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
import typer
from helpers import _FakeTask, load_script_module

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


def test_main_samples_tasks_and_runs_checks(monkeypatch) -> None:
    generation_calls: list[tuple[str, object | None]] = []
    checked_task_ids: list[str] = []
    per_family_idx: dict[str, int] = {}

    def _fake_generate_task_for_family(family: str, rng, axes):  # noqa: ANN001
        del rng
        generation_calls.append((family, axes))
        idx = per_family_idx.get(family, 0)
        per_family_idx[family] = idx + 1
        return _FakeTask(f"{family}-{idx}")

    def _fake_check(tasks: list[_FakeTask]) -> None:
        checked_task_ids.extend(task.task_id for task in tasks)

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_task_for_family",
        _fake_generate_task_for_family,
    )
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

    assert generation_calls == [
        ("piecewise", None),
        ("piecewise", None),
        ("stateful", None),
        ("stateful", None),
    ]
    assert checked_task_ids == [
        "piecewise-0",
        "piecewise-1",
        "stateful-0",
        "stateful-1",
    ]


def test_main_raises_for_insufficient_unique_tasks(monkeypatch) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_task_for_family",
        lambda family, rng, axes: _FakeTask(f"{family}-same"),  # noqa: ARG005
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    with pytest.raises(typer.BadParameter, match="produced only 1 unique task"):
        check_generated_code_quality_main(
            families="piecewise",
            seed=7,
            count_per_family=2,
            pool_size=4,
        )


def test_main_exits_when_quality_checks_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_task_for_family",
        lambda family, rng, axes: _FakeTask(f"{family}-{rng.random()}"),  # noqa: ARG005
    )

    def _raise_quality_error(tasks: list[_FakeTask]) -> None:  # noqa: ARG001
        raise _SCRIPT_MODULE.GeneratedCodeQualityError("quality failure")

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        _raise_quality_error,
    )

    with pytest.raises(typer.Exit) as exc_info:
        check_generated_code_quality_main(
            families="piecewise",
            seed=7,
            count_per_family=2,
            pool_size=4,
        )

    assert exc_info.value.exit_code == 1
