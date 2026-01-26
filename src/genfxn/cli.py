import random
from pathlib import Path
from typing import Annotated

import srsly
import typer

from genfxn.core.models import Task
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.splits import AxisHoldout, HoldoutType, split_tasks
from genfxn.stateful.task import generate_stateful_task

app = typer.Typer(help="Generate and split function synthesis tasks.")


@app.command()
def generate(
    output: Annotated[Path, typer.Option("--output", "-o", help="Output JSONL file")],
    family: Annotated[
        str, typer.Option("--family", "-f", help="piecewise, stateful, or all")
    ] = "all",
    count: Annotated[int, typer.Option("--count", "-n", help="Number of tasks")] = 100,
    seed: Annotated[
        int | None, typer.Option("--seed", "-s", help="Random seed")
    ] = None,
) -> None:
    """Generate tasks to JSONL file."""
    rng = random.Random(seed)
    tasks: list[Task] = []

    if family == "all":
        half = count // 2
        for _ in range(half):
            tasks.append(generate_piecewise_task(rng=rng))
        for _ in range(count - half):
            tasks.append(generate_stateful_task(rng=rng))
    elif family == "piecewise":
        for _ in range(count):
            tasks.append(generate_piecewise_task(rng=rng))
    elif family == "stateful":
        for _ in range(count):
            tasks.append(generate_stateful_task(rng=rng))
    else:
        typer.echo(f"Unknown family: {family}", err=True)
        raise typer.Exit(1)

    srsly.write_jsonl(output, [t.model_dump() for t in tasks])
    typer.echo(f"Generated {len(tasks)} tasks to {output}")


@app.command()
def split(
    input_file: Annotated[Path, typer.Argument(help="Input JSONL file")],
    train: Annotated[Path, typer.Option("--train", help="Train output JSONL")],
    test: Annotated[Path, typer.Option("--test", help="Test output JSONL")],
    holdout_axis: Annotated[
        str, typer.Option("--holdout-axis", help="Dot-path to spec field")
    ],
    holdout_value: Annotated[
        str, typer.Option("--holdout-value", help="Value to hold out")
    ],
    holdout_type: Annotated[
        str, typer.Option("--holdout-type", help="exact, range, or contains")
    ] = "exact",
) -> None:
    """Split tasks using axis holdouts."""
    raw = list(srsly.read_jsonl(input_file))
    tasks = [Task(**t) for t in raw]

    parsed_value: str | tuple[int, int] = holdout_value
    if holdout_type == "range":
        lo, hi = holdout_value.split(",")
        parsed_value = (int(lo), int(hi))

    holdouts = [
        AxisHoldout(
            axis_path=holdout_axis,
            holdout_type=HoldoutType(holdout_type),
            holdout_value=parsed_value,
        )
    ]
    result = split_tasks(tasks, holdouts)

    srsly.write_jsonl(train, [t.model_dump() for t in result.train])
    srsly.write_jsonl(test, [t.model_dump() for t in result.test])
    typer.echo(f"Train: {len(result.train)}, Test: {len(result.test)}")


@app.command()
def info(
    input_file: Annotated[Path, typer.Argument(help="Input JSONL file")],
) -> None:
    """Show info about tasks file."""
    raw = list(srsly.read_jsonl(input_file))
    tasks = [Task(**t) for t in raw]

    by_family: dict[str, int] = {}
    for t in tasks:
        by_family[t.family] = by_family.get(t.family, 0) + 1

    typer.echo(f"{input_file}: {len(tasks)} tasks")
    for fam, cnt in sorted(by_family.items()):
        typer.echo(f"  {fam}: {cnt}")
