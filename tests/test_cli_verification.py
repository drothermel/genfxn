import random
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import srsly
from typer.testing import CliRunner

import genfxn.cli as cli_module
from genfxn.cli import app
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.verification.io import verification_sidecar_paths
from genfxn.verification.models import (
    VerificationCase,
    VerificationFailure,
    VerificationLayer,
    VerificationMetrics,
)

runner = CliRunner()


def _placeholder_artifacts(tasks: list[object]) -> SimpleNamespace:
    cases = []
    metrics = []
    for idx, task in enumerate(tasks):
        task_id = cast(str, getattr(task, "task_id"))
        family = cast(str, getattr(task, "family"))
        cases.append(
            VerificationCase(
                task_id=task_id,
                family=family,
                layer=VerificationLayer.LAYER1_SPEC_BOUNDARY,
                case_id=f"layer1-{idx:04d}",
                input=0,
                expected_output=0,
            )
        )
        metrics.append(
            VerificationMetrics(
                task_id=task_id,
                family=family,
                n_layer1_cases=1,
                n_layer2_cases=0,
                n_layer3_cases=0,
                mutation_score=1.0,
                mutation_score_curve=[],
                heldout_mutant_fpr=0.0,
                heldout_mutant_fpr_ci95=0.0,
            )
        )
    return SimpleNamespace(cases=cases, metrics=metrics)


def test_generate_emits_sidecars_and_verify_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "2",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0
    assert output.exists()

    cases_path, metrics_path = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
    assert cases_path.exists()
    assert metrics_path.exists()
    rows = cast(list[dict], list(srsly.read_jsonl(cases_path)))
    layer2_rows = [row for row in rows if row.get("layer") == "layer2_property"]
    assert layer2_rows
    assert all(
        row.get("source_detail", {}).get("generator") == "hypothesis"
        for row in layer2_rows
    )

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
            "--no-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 0
    assert "Verified 2 task(s)" in verify_result.stdout


def test_generate_fails_atomically_on_verification_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    def _fake_verify_cases(
        *args: object,
        **kwargs: object,  # noqa: ARG001
    ) -> list[VerificationFailure]:
        tasks = cast(list, args[0])
        return [
            VerificationFailure(
                task_id=tasks[0].task_id,
                family=tasks[0].family,
                case_id="layer1-0000",
                message="forced failure",
            )
        ]

    monkeypatch.setattr(cli_module, "verify_cases", _fake_verify_cases)

    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "1",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert result.exit_code == 1
    assert not output.exists()
    cases_path, metrics_path = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
    assert not cases_path.exists()
    assert not metrics_path.exists()


def test_generate_rolls_back_outputs_when_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )
    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    cases_path, metrics_path = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )

    original_replace = cli_module.os.replace
    failed_once = False

    def _fail_dataset_replace(src: object, dst: object) -> None:
        nonlocal failed_once
        destination = Path(dst)
        if destination == output and not failed_once:
            failed_once = True
            raise OSError("simulated output commit failure")
        original_replace(src, dst)

    monkeypatch.setattr(cli_module.os, "replace", _fail_dataset_replace)

    result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "1",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert result.exit_code == 1
    assert not output.exists()
    assert not cases_path.exists()
    assert not metrics_path.exists()


def test_verify_fails_when_sidecar_case_is_tampered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "1",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0

    cases_path, _ = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
    rows = cast(list[dict], list(srsly.read_jsonl(cases_path)))
    assert rows
    expected = rows[0]["expected_output"]
    if isinstance(expected, int):
        rows[0]["expected_output"] = expected + 1
    elif isinstance(expected, list):
        rows[0]["expected_output"] = [*expected, "__TAMPERED__"]
    elif isinstance(expected, dict):
        rows[0]["expected_output"] = {**expected, "_tampered": True}
    else:
        rows[0]["expected_output"] = "__TAMPERED__"
    srsly.write_jsonl(cases_path, rows)

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
            "--no-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 1
    assert "Verification failed" in verify_result.output


def test_verify_warns_when_sidecars_missing_and_regenerates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "1",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0

    cases_path, metrics_path = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
    cases_path.unlink()
    assert not cases_path.exists()
    assert metrics_path.exists()

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
            "--no-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 0
    assert "Warning: requested sidecar reuse" in verify_result.output
    assert str(cases_path) in verify_result.output
    assert cases_path.exists()


def test_verify_regenerates_when_sidecars_are_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "1",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0

    cases_path, _ = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
    cases_path.write_text("{broken-json\n", encoding="utf-8")

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
            "--no-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 0
    assert (
        "Warning: failed to load verification sidecars" in verify_result.output
    )


def test_verify_fails_when_sidecars_miss_dataset_task_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )

    output = tmp_path / "tasks.jsonl"
    verification_dir = tmp_path / "verification_cases"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "2",
            "--no-verify-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0

    dataset_rows = cast(list[dict], list(srsly.read_jsonl(output)))
    assert len(dataset_rows) == 2
    removed_task_id = cast(str, dataset_rows[0]["task_id"])

    cases_path, _ = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
    case_rows = cast(list[dict], list(srsly.read_jsonl(cases_path)))
    filtered_rows = [
        row for row in case_rows if row.get("task_id") != removed_task_id
    ]
    srsly.write_jsonl(cases_path, filtered_rows)

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
            "--no-full",
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 1
    assert (
        "Verification sidecar coverage validation failed"
        in verify_result.output
    )
    assert "missing verification cases for task_id(s)" in verify_result.output


def test_generate_uses_full_parity_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,  # noqa: ARG005
    )
    monkeypatch.setattr(
        cli_module,
        "build_verification_artifacts",
        lambda tasks, **kwargs: _placeholder_artifacts(tasks),  # noqa: ARG005
    )
    seen_full_parity: list[bool] = []

    def _fake_verify_cases(*args: object, **kwargs: object) -> list[object]:
        seen_full_parity.append(bool(kwargs.get("full_parity")))
        return []

    monkeypatch.setattr(cli_module, "verify_cases", _fake_verify_cases)

    output = tmp_path / "tasks.jsonl"
    result = runner.invoke(
        app,
        [
            "generate",
            "-o",
            str(output),
            "-f",
            "piecewise",
            "-n",
            "1",
            "--verification-output-dir",
            str(tmp_path / "verification_cases"),
        ],
    )

    assert result.exit_code == 0
    assert seen_full_parity == [True]


def test_verify_uses_full_parity_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = generate_piecewise_task(rng=random.Random(5)).model_dump(mode="json")
    dataset = tmp_path / "tasks.jsonl"
    srsly.write_jsonl(dataset, [task])

    monkeypatch.setattr(
        cli_module,
        "build_verification_artifacts",
        lambda tasks, **kwargs: _placeholder_artifacts(tasks),  # noqa: ARG005
    )
    seen_full_parity: list[bool] = []

    def _fake_verify_cases(*args: object, **kwargs: object) -> list[object]:
        seen_full_parity.append(bool(kwargs.get("full_parity")))
        return []

    monkeypatch.setattr(cli_module, "verify_cases", _fake_verify_cases)

    result = runner.invoke(
        app,
        [
            "verify",
            str(dataset),
            "--regenerate-sidecars",
            "--no-write-sidecars",
            "--verification-output-dir",
            str(tmp_path / "verification_cases"),
        ],
    )

    assert result.exit_code == 0
    assert seen_full_parity == [True]
