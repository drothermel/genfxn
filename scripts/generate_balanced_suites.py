"""Generate balanced task suites per (family, difficulty) combination."""

from pathlib import Path

import srsly
import typer

from genfxn.suites.generate import generate_suite, quota_report

app = typer.Typer()

ALL_FAMILIES = ["stringrules", "stateful", "simple_algorithms"]
ALL_DIFFICULTIES = [3, 4, 5]


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
    difficulties: str = typer.Option(
        "all",
        help="Comma-separated difficulty levels or 'all'",
    ),
) -> None:
    """Generate balanced 50-task suites per (family, difficulty)."""
    family_list = ALL_FAMILIES if families == "all" else families.split(",")
    diff_list = (
        ALL_DIFFICULTIES
        if difficulties == "all"
        else [int(d) for d in difficulties.split(",")]
    )

    for family in family_list:
        for difficulty in diff_list:
            typer.echo(f"\n{'=' * 60}")
            typer.echo(f"Generating {family} D{difficulty}...")
            typer.echo(f"{'=' * 60}")

            tasks = generate_suite(
                family=family,
                difficulty=difficulty,
                seed=seed,
                pool_size=pool_size,
            )

            typer.echo(f"Selected {len(tasks)} tasks")

            # Write to JSONL
            out_path = output_dir / family / f"level_{difficulty}" / "all.jsonl"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            records = [t.model_dump(mode="json") for t in tasks]
            srsly.write_jsonl(str(out_path), records)
            typer.echo(f"Written to {out_path}")

            # Print quota report
            report = quota_report(tasks, family, difficulty)
            hdr = f"\n{'Axis':<40} {'Value':<12} "
            hdr += f"{'Target':>6} {'Got':>6} Status"
            typer.echo(hdr)
            typer.echo("-" * 75)
            for axis, value, target, achieved, status in report:
                m = "  " if status == "OK" else "!!"
                typer.echo(
                    f"{m} {axis:<38} {value:<12} "
                    f"{target:>6} {achieved:>6} {status}"
                )


if __name__ == "__main__":
    app()
