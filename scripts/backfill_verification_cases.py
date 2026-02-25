"""Generate verification sidecars for an existing dataset JSONL file."""

from __future__ import annotations

from pathlib import Path

import srsly
import typer
from pydantic import ValidationError

from genfxn.core.models import Task
from genfxn.verification.io import (
    DEFAULT_VERIFICATION_OUTPUT_DIR,
    verification_sidecar_paths,
    write_verification_sidecars,
)
from genfxn.verification.runner import (
    build_verification_artifacts,
    summarize_case_counts,
    verify_cases,
)

app = typer.Typer()


@app.command()
def main(
    input_file: Path = typer.Argument(help="Input dataset JSONL file."),
    verification_output_dir: Path = typer.Option(
        DEFAULT_VERIFICATION_OUTPUT_DIR,
        help="Output directory for verification sidecars.",
    ),
    verification_seed: int = typer.Option(
        0,
        help="Deterministic seed for verification-case generation.",
    ),
    verify_full: bool = typer.Option(
        True,
        "--verify-full/--no-verify-full",
        help="Run full parity replay checks when generating sidecars.",
    ),
) -> None:
    tasks: list[Task] = []
    for line_number, row in enumerate(srsly.read_jsonl(input_file), start=1):
        try:
            tasks.append(Task.model_validate(row))
        except ValidationError as exc:
            raise typer.BadParameter(
                f"Line {line_number}: task schema validation failed: {exc}"
            ) from exc

    try:
        artifacts = build_verification_artifacts(tasks, seed=verification_seed)
    except ValueError as exc:
        typer.echo(
            f"Failed to build verification artifacts: {exc}",
            err=True,
        )
        raise typer.Exit(1) from exc
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            f"Unexpected verification artifact build failure: {exc}",
            err=True,
        )
        raise typer.Exit(1) from exc

    failures = verify_cases(
        tasks,
        artifacts.cases,
        full_parity=verify_full,
    )
    if failures:
        typer.echo(
            f"Verification failed with {len(failures)} mismatch(es).",
            err=True,
        )
        for failure in failures[:20]:
            typer.echo(
                (
                    f"- {failure.task_id} [{failure.family}] "
                    f"{failure.case_id}: {failure.message}"
                ),
                err=True,
            )
        raise typer.Exit(1)

    cases_path, metrics_path = verification_sidecar_paths(
        input_file,
        output_dir=verification_output_dir,
    )
    try:
        write_verification_sidecars(
            cases_path,
            metrics_path,
            cases=artifacts.cases,
            metrics=artifacts.metrics,
        )
    except OSError as exc:
        typer.echo(
            f"Failed to write verification sidecars: {exc}",
            err=True,
        )
        raise typer.Exit(1) from exc

    counts = summarize_case_counts(artifacts.cases)
    typer.echo(
        f"Wrote sidecars for {len(tasks)} task(s): {cases_path}, {metrics_path}"
    )
    typer.echo(
        "Case counts by layer: "
        f"layer1={counts.get('layer1_spec_boundary', 0)}, "
        f"layer2={counts.get('layer2_property', 0)}, "
        f"layer3={counts.get('layer3_mutation', 0)}"
    )


if __name__ == "__main__":
    app()
