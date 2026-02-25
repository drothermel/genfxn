import random
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import srsly
import typer
from helpers import load_script_module

from genfxn.piecewise.task import generate_piecewise_task

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "backfill_verification_cases.py"
)

_SCRIPT_MODULE = load_script_module(
    _SCRIPT, "tests.backfill_verification_cases_script_module"
)
backfill_verification_cases_main = cast(
    Callable[..., None], _SCRIPT_MODULE.main
)


def test_main_writes_sidecars_for_dataset(tmp_path: Path) -> None:
    task = generate_piecewise_task(rng=random.Random(3)).model_dump(mode="json")
    input_file = tmp_path / "dataset.jsonl"
    srsly.write_jsonl(input_file, [task])

    output_dir = tmp_path / "verification_cases"
    backfill_verification_cases_main(
        input_file=input_file,
        verification_output_dir=output_dir,
        verification_seed=0,
        verify_full=False,
    )

    cases_path = output_dir / "dataset.verification_cases.jsonl"
    metrics_path = output_dir / "dataset.verification_metrics.jsonl"
    assert cases_path.exists()
    assert metrics_path.exists()
    assert list(srsly.read_jsonl(cases_path))
    assert list(srsly.read_jsonl(metrics_path))


def test_main_exits_when_verification_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = generate_piecewise_task(rng=random.Random(3)).model_dump(mode="json")
    input_file = tmp_path / "dataset.jsonl"
    srsly.write_jsonl(input_file, [task])

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "verify_cases",
        lambda *_args, **_kwargs: [
            SimpleNamespace(
                task_id="task",
                family="piecewise",
                case_id="case-1",
                message="mismatch",
            )
        ],
    )

    with pytest.raises(typer.Exit) as exc_info:
        backfill_verification_cases_main(
            input_file=input_file,
            verification_output_dir=tmp_path / "verification_cases",
            verification_seed=0,
            verify_full=False,
        )
    assert exc_info.value.exit_code == 1
