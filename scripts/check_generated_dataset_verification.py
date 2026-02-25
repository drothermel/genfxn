"""Deterministic generated-dataset verification gate for CI/local checks."""

from __future__ import annotations

import random

import typer

from genfxn.core.family_registry import (
    generate_task_for_family,
    parse_family_selector,
)
from genfxn.verification.runner import (
    build_verification_artifacts,
    verify_cases,
)

app = typer.Typer()


@app.command()
def main(
    families: str = typer.Option(
        "all",
        help="Comma-separated families or 'all'.",
    ),
    seed: int = typer.Option(42, help="Deterministic seed."),
    sample_per_family: int = typer.Option(
        3,
        help="Number of tasks sampled per family.",
    ),
    mutation_score_floor: float = typer.Option(
        0.70,
        help="Minimum mutation_score required per task.",
    ),
    verify_full: bool = typer.Option(
        True,
        "--verify-full/--no-verify-full",
        help="Run full verification mode parity hooks.",
    ),
) -> None:
    if sample_per_family <= 0:
        raise typer.BadParameter("sample_per_family must be > 0")
    if mutation_score_floor < 0.0 or mutation_score_floor > 1.0:
        raise typer.BadParameter("mutation_score_floor must be in [0.0, 1.0]")

    try:
        selected_families = parse_family_selector(families)
    except ValueError as err:
        raise typer.BadParameter(str(err)) from err

    sampled_tasks = []
    for family_idx, family in enumerate(selected_families):
        seen_task_ids: set[str] = set()
        sampled_for_family = []
        attempt_budget = max(sample_per_family * 8, sample_per_family)
        for attempt in range(attempt_budget):
            rng = random.Random(seed + family_idx * 10_000 + attempt)
            task = generate_task_for_family(family, rng=rng, axes=None)
            if task.task_id in seen_task_ids:
                continue
            seen_task_ids.add(task.task_id)
            sampled_for_family.append(task)
            if len(sampled_for_family) >= sample_per_family:
                break

        if len(sampled_for_family) < sample_per_family:
            unique_label = "task" if len(sampled_for_family) == 1 else "tasks"
            raise typer.BadParameter(
                "Family "
                f"'{family}' produced only {len(sampled_for_family)} unique "
                f"{unique_label} "
                f"with attempt_budget={attempt_budget}; need "
                f"{sample_per_family}."
            )

        sampled_tasks.extend(sampled_for_family)

    try:
        artifacts = build_verification_artifacts(sampled_tasks, seed=seed)
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            f"Failed to build verification artifacts: {exc}",
            err=True,
        )
        raise typer.Exit(1) from exc
    failures = verify_cases(
        sampled_tasks,
        artifacts.cases,
        full_parity=verify_full,
    )
    if failures:
        typer.echo(f"Verification mismatches: {len(failures)}", err=True)
        for failure in failures[:20]:
            typer.echo(
                (
                    f"- {failure.task_id} [{failure.family}] "
                    f"{failure.case_id}: {failure.message}"
                ),
                err=True,
            )
        raise typer.Exit(1)

    low_scores = [
        metric
        for metric in artifacts.metrics
        if metric.mutation_score < mutation_score_floor
    ]
    if low_scores:
        typer.echo(
            "Mutation score gate failed for generated dataset verification:",
            err=True,
        )
        for metric in low_scores[:20]:
            typer.echo(
                (
                    f"- {metric.task_id} [{metric.family}] "
                    f"mutation_score={metric.mutation_score:.3f} "
                    f"< {mutation_score_floor:.3f}"
                ),
                err=True,
            )
        raise typer.Exit(1)

    typer.echo(
        "Generated dataset verification passed for "
        f"{len(sampled_tasks)} tasks across {len(selected_families)} "
        "families."
    )


if __name__ == "__main__":
    app()
