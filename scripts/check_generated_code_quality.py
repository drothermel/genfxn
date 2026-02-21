"""Generate deterministic task samples and validate Java/Rust code quality."""

from __future__ import annotations

import typer

from genfxn.generated_code_quality import (
    GeneratedCodeQualityError,
    check_generated_code_quality,
)
from genfxn.suites.generate import generate_pool
from genfxn.suites.quotas import QUOTAS

app = typer.Typer()


def _parse_families(families: str) -> list[str]:
    if families == "all":
        return sorted(QUOTAS.keys())

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
    families: str = typer.Option(
        "all",
        help="Comma-separated families or 'all'",
    ),
    seed: int = typer.Option(42, help="Random seed"),
    count_per_family: int = typer.Option(
        2, help="Deterministic tasks checked per family"
    ),
    pool_size: int = typer.Option(
        20, help="Candidate pool size used to sample tasks per family"
    ),
) -> None:
    """Run generated-code style/lint checks on deterministic sampled tasks."""
    if count_per_family <= 0:
        raise typer.BadParameter("count_per_family must be > 0")
    if pool_size <= 0:
        raise typer.BadParameter("pool_size must be > 0")
    if pool_size < count_per_family:
        raise typer.BadParameter("pool_size must be >= count_per_family")

    selected_families = _parse_families(families)
    tasks = []

    for idx, family in enumerate(selected_families):
        family_seed = seed + idx * 10_000
        candidates, stats = generate_pool(
            family=family,
            seed=family_seed,
            pool_size=pool_size,
        )
        if len(candidates) < count_per_family:
            raise typer.BadParameter(
                f"Family '{family}' produced only {len(candidates)} "
                f"candidate tasks (errors={stats.errors}, "
                f"duplicates={stats.duplicates}); need {count_per_family}."
            )
        tasks.extend(
            candidate.task for candidate in candidates[:count_per_family]
        )

    try:
        check_generated_code_quality(tasks)
    except GeneratedCodeQualityError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1) from err

    typer.echo(
        "Generated-code quality checks passed for "
        f"{len(tasks)} tasks across {len(selected_families)} families."
    )


if __name__ == "__main__":
    app()
