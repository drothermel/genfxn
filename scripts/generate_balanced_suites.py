"""Generate balanced task suites per family."""

from pathlib import Path

import srsly
import typer

from genfxn.generated_code_quality import (
    GeneratedCodeQualityError,
    check_generated_code_quality,
)
from genfxn.suites.generate import generate_suite, quota_report
from genfxn.suites.quotas import QUOTAS

app = typer.Typer()


def _parse_families(families: str) -> list[str]:
    if families == "all":
        return list(QUOTAS.keys())

    family_list = [
        family.strip() for family in families.split(",") if family.strip()
    ]
    if not family_list:
        raise typer.BadParameter("families must not be empty")

    invalid = [family for family in family_list if family not in QUOTAS]
    if invalid:
        invalid_str = ", ".join(invalid)
        valid = ", ".join(sorted(QUOTAS.keys()))
        raise typer.BadParameter(
            f"Invalid families: {invalid_str}. Valid options: {valid}"
        )
    return family_list


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
    family_list = _parse_families(families)

    for family in family_list:
        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Generating {family} suite...")
        typer.echo(f"{'=' * 60}")

        tasks = generate_suite(
            family=family,
            seed=seed,
            pool_size=pool_size,
        )

        if not skip_generated_style_checks:
            try:
                check_generated_code_quality(tasks)
            except GeneratedCodeQualityError as err:
                typer.echo(str(err), err=True)
                raise typer.Exit(1) from err

        typer.echo(f"Selected {len(tasks)} tasks")

        out_path = output_dir / family / "all.jsonl"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        records = [task.model_dump(mode="json") for task in tasks]
        srsly.write_jsonl(str(out_path), records)
        typer.echo(f"Written to {out_path}")

        report = quota_report(tasks, family)
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
