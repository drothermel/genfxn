from pathlib import Path
from typing import cast

import pytest
import srsly
from typer.testing import CliRunner

import genfxn.cli as cli_module
from genfxn.cli import app
from genfxn.verification.io import verification_sidecar_paths
from genfxn.verification.models import VerificationFailure

runner = CliRunner()


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

    cases_path, metrics_path = verification_sidecar_paths(
        output,
        output_dir=verification_dir,
    )
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
            "--verification-output-dir",
            str(verification_dir),
        ],
    )
    assert verify_result.exit_code == 0
    assert "Warning: requested sidecar reuse" in verify_result.output
    assert str(cases_path) in verify_result.output
    assert cases_path.exists()
