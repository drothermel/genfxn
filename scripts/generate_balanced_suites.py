"""Generate balanced task suites per (family, difficulty) combination."""

from pathlib import Path

import srsly
import typer

from genfxn.suites.generate import generate_suite, quota_report
from genfxn.suites.quotas import QUOTAS

app = typer.Typer()


def _parse_families(families: str) -> list[str]:
    if families == "all":
        return list(QUOTAS.keys())

    family_list = [f.strip() for f in families.split(",") if f.strip()]
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


def _parse_difficulties(difficulties: str) -> list[int] | None:
    if difficulties == "all":
        return None

    try:
        difficulty_list = [
            int(d.strip()) for d in difficulties.split(",") if d.strip()
        ]
    except ValueError as exc:
        raise typer.BadParameter(
            "difficulties must be comma-separated integers or 'all'"
        ) from exc

    if not difficulty_list:
        raise typer.BadParameter("difficulties must not be empty")

    return difficulty_list


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
    family_list = _parse_families(families)
    requested_difficulties = _parse_difficulties(difficulties)

    for family in family_list:
        family_difficulties = list(QUOTAS[family].keys())
        if requested_difficulties is None:
            diff_list = family_difficulties
        else:
            supported = set(family_difficulties)
            diff_list = [d for d in requested_difficulties if d in supported]
            skipped = [d for d in requested_difficulties if d not in supported]

            for difficulty in skipped:
                typer.echo(
                    f"Skipping {family} D{difficulty}: not available in QUOTAS"
                )
            if not diff_list:
                typer.echo(
                    f"Skipping {family}: no requested difficulties available"
                )
                continue

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
