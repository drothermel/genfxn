from pathlib import Path
from typing import cast

import pytest
import srsly
from typer.testing import CliRunner

import genfxn.cli as cli_module
from genfxn.cli import app
from genfxn.verification.models import VerificationFailure

runner = CliRunner()


def _sidecar_paths(
    verification_dir: Path,
    dataset_path: Path,
) -> tuple[Path, Path]:
    stem = dataset_path.stem
    return (
        verification_dir / f"{stem}.verification_cases.jsonl",
        verification_dir / f"{stem}.verification_metrics.jsonl",
    )


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
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0
    assert output.exists()

    cases_path, metrics_path = _sidecar_paths(verification_dir, output)
    assert cases_path.exists()
    assert metrics_path.exists()

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
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
    monkeypatch.setattr(
        cli_module,
        "verify_cases",
        lambda tasks, cases, full_parity=False: [  # noqa: ARG005
            VerificationFailure(
                task_id=tasks[0].task_id,
                family=tasks[0].family,
                case_id="layer1-0000",
                message="forced failure",
            )
        ],
    )

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
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert result.exit_code == 1
    assert not output.exists()
    cases_path, metrics_path = _sidecar_paths(verification_dir, output)
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
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0

    cases_path, _ = _sidecar_paths(verification_dir, output)
    rows = cast(list[dict], list(srsly.read_jsonl(cases_path)))
    assert rows
    rows[0]["expected_output"] = rows[0]["expected_output"] + 1
    srsly.write_jsonl(cases_path, rows)

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
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
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert generate_result.exit_code == 0

    cases_path, metrics_path = _sidecar_paths(verification_dir, output)
    cases_path.unlink()
    assert not cases_path.exists()
    assert metrics_path.exists()

    verify_result = runner.invoke(
        app,
        [
            "verify",
            str(output),
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 0
    assert "Warning: requested sidecar reuse" in verify_result.output
    assert str(cases_path) in verify_result.output
    assert cases_path.exists()
