"""Generate deterministic task samples and validate Java/Rust code quality."""

from __future__ import annotations

import random

import typer

from genfxn.core.family_registry import (
    generate_task_for_family,
    parse_family_selector,
)
from genfxn.generated_code_quality import (
    GeneratedCodeQualityError,
    check_generated_code_quality,
)

app = typer.Typer()


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
        20,
        help=(
            "Deterministic sample attempt budget per family. Must be >= "
            "count-per-family."
        ),
    ),
) -> None:
    """Run generated-code style/lint checks on deterministic sampled tasks."""
    if count_per_family <= 0:
        raise typer.BadParameter("count_per_family must be > 0")
    if pool_size <= 0:
        raise typer.BadParameter("pool_size must be > 0")
    if pool_size < count_per_family:
        raise typer.BadParameter("pool_size must be >= count_per_family")

    try:
        selected_families = parse_family_selector(families)
    except ValueError as err:
        raise typer.BadParameter(str(err)) from err

    tasks = []
    for idx, family in enumerate(selected_families):
        family_seed = seed + idx * 10_000
        seen_task_ids: set[str] = set()
        sampled = []

        for attempt in range(pool_size):
            task = generate_task_for_family(
                family,
                rng=random.Random(family_seed + attempt),
                axes=None,
            )
            if task.task_id in seen_task_ids:
                continue
            seen_task_ids.add(task.task_id)
            sampled.append(task)
            if len(sampled) >= count_per_family:
                break

        if len(sampled) < count_per_family:
            unique_label = "task" if len(sampled) == 1 else "tasks"
            raise typer.BadParameter(
                "Family "
                f"'{family}' produced only {len(sampled)} "
                f"unique {unique_label} "
                f"with pool_size={pool_size}; need {count_per_family}."
            )
        tasks.extend(sampled)

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
