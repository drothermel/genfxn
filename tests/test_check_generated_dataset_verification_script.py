from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import typer
from helpers import _FakeMetric, _FakeTask, load_script_module

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "check_generated_dataset_verification.py"
)

_SCRIPT_MODULE = load_script_module(
    _SCRIPT, "tests.check_generated_dataset_verification_script_module"
)
check_generated_dataset_verification_main = cast(
    Callable[..., None], _SCRIPT_MODULE.main
)


def test_main_passes_with_sufficient_mutation_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated: list[_FakeTask] = []
    built_with_seed: list[int] = []

    def _fake_generate_task_for_family(family: str, rng, axes):  # noqa: ANN001
        del rng, axes
        task = _FakeTask(f"{family}-{len(generated)}", family)
        generated.append(task)
        return task

    def _fake_build_verification_artifacts(tasks, seed: int):  # noqa: ANN001
        built_with_seed.append(seed)
        metrics = [
            _FakeMetric(
                task_id=task.task_id, family=task.family, mutation_score=0.8
            )
            for task in tasks
        ]
        return SimpleNamespace(cases=["case"], metrics=metrics)

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_task_for_family",
        _fake_generate_task_for_family,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "build_verification_artifacts",
        _fake_build_verification_artifacts,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "verify_cases",
        lambda *args, **kwargs: [],  # noqa: ARG005
    )

    check_generated_dataset_verification_main(
        families="piecewise,stateful",
        seed=11,
        sample_per_family=2,
        mutation_score_floor=0.7,
        verify_full=False,
    )

    assert len(generated) == 4
    assert built_with_seed == [11]


def test_main_exits_on_verification_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_task_for_family",
        lambda family, rng, axes: _FakeTask(f"{family}-0", family),  # noqa: ARG005
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "build_verification_artifacts",
        lambda tasks, seed: SimpleNamespace(  # noqa: ARG005
            cases=["case"],
            metrics=[_FakeMetric(tasks[0].task_id, tasks[0].family, 1.0)],
        ),
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "verify_cases",
        lambda tasks, cases, full_parity: [  # noqa: ARG005
            SimpleNamespace(
                task_id=tasks[0].task_id,
                family=tasks[0].family,
                case_id="case-1",
                message="mismatch",
            )
        ],
    )

    with pytest.raises(typer.Exit) as exc_info:
        check_generated_dataset_verification_main(
            families="piecewise",
            seed=3,
            sample_per_family=1,
            mutation_score_floor=0.7,
            verify_full=False,
        )
    assert exc_info.value.exit_code == 1


def test_main_exits_on_low_mutation_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_task_for_family",
        lambda family, rng, axes: _FakeTask(f"{family}-0", family),  # noqa: ARG005
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "build_verification_artifacts",
        lambda tasks, seed: SimpleNamespace(  # noqa: ARG005
            cases=[],
            metrics=[_FakeMetric(tasks[0].task_id, tasks[0].family, 0.2)],
        ),
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "verify_cases",
        lambda *args, **kwargs: [],  # noqa: ARG005
    )

    with pytest.raises(typer.Exit) as exc_info:
        check_generated_dataset_verification_main(
            families="piecewise",
            seed=3,
            sample_per_family=1,
            mutation_score_floor=0.7,
            verify_full=False,
        )
    assert exc_info.value.exit_code == 1
