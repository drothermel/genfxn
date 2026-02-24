"""Generate balanced task suites per family."""

import os
import tempfile
from pathlib import Path

import srsly
import typer

from genfxn.generated_code_quality import (
    GeneratedCodeQualityError,
    check_generated_code_quality,
    validate_generated_code_quality_tools,
)
from genfxn.suites.families import parse_families
from genfxn.suites.generate import generate_suite, quota_report

app = typer.Typer()


def _write_jsonl_atomically(
    path: Path, records: list[dict[str, object]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(srsly.json_dumps(record))
                handle.write("\n")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.command()
def main(
    output_dir: Path = typer.Option(
        Path("data/balanced_suites"),
        help="Output directory for generated suites",
    ),
    seed: int = typer.Option(42, help="Random seed"),
    pool_size: int = typer.Option(3000, help="Initial candidate pool size"),
    families: str = typer.Option(
        "all",
        help="Comma-separated families or 'all'",
    ),
    skip_generated_style_checks: bool = typer.Option(
        False,
        help="Skip Java/Rust generated-code style/lint checks.",
    ),
) -> None:
    """Generate balanced 50-task suites per family."""
    family_list = parse_families(families)
    generated: dict[str, list] = {}
    reports: dict[str, list[tuple[str, str, int, int, str]]] = {}

    if not skip_generated_style_checks:
        try:
            validate_generated_code_quality_tools()
        except GeneratedCodeQualityError as err:
            typer.echo(str(err), err=True)
            raise typer.Exit(1) from err

    for family in family_list:
        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Generating and validating {family} suite...")
        typer.echo(f"{'=' * 60}")

        tasks = generate_suite(
            family=family,
            seed=seed,
            pool_size=pool_size,
        )

        if not skip_generated_style_checks:
            try:
                check_generated_code_quality(tasks, validate_tools=False)
            except GeneratedCodeQualityError as err:
                typer.echo(str(err), err=True)
                raise typer.Exit(1) from err

        generated[family] = tasks
        reports[family] = quota_report(tasks, family)
        typer.echo(f"Validated {len(tasks)} tasks for {family}")

    typer.echo(f"\n{'=' * 60}")
    typer.echo("All suites validated. Writing output files...")
    typer.echo(f"{'=' * 60}")

    for family in family_list:
        tasks = generated[family]
        out_path = output_dir / family / "all.jsonl"
        records = [task.model_dump(mode="json") for task in tasks]
        _write_jsonl_atomically(out_path, records)
        typer.echo(f"Written to {out_path}")

        report = reports[family]
        if not report:
            typer.echo("No bucket quotas configured for this family.")
            continue

        hdr = f"\n{'Axis':<40} {'Value':<12} {'Target':>6} {'Got':>6} Status"
        typer.echo(hdr)
        typer.echo("-" * 75)
        for axis, value, target, achieved, status in report:
            marker = "  " if status == "OK" else "!!"
            typer.echo(
                f"{marker} {axis:<38} {value:<12} "
                f"{target:>6} {achieved:>6} {status}"
            )


if __name__ == "__main__":
    app()
