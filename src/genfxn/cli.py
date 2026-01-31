import random
from pathlib import Path
from typing import Annotated

import srsly
import typer

from genfxn.core.models import Task
from genfxn.core.predicates import PredicateType
from genfxn.core.transforms import TransformType
from genfxn.piecewise.models import ExprType, PiecewiseAxes
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.splits import AxisHoldout, HoldoutType, random_split, split_tasks
from genfxn.stateful.models import StatefulAxes, TemplateType
from genfxn.stateful.task import generate_stateful_task

app = typer.Typer(help="Generate and split function synthesis tasks.")


def _parse_range(value: str | None) -> tuple[int, int] | None:
    """Parse 'lo,hi' string into tuple."""
    if value is None:
        return None
    lo, hi = value.split(",")
    return (int(lo.strip()), int(hi.strip()))


def _build_stateful_axes(
    templates: str | None,
    predicate_types: str | None,
    transform_types: str | None,
    value_range: str | None,
    threshold_range: str | None,
    divisor_range: str | None,
    list_length_range: str | None,
    shift_range: str | None,
    scale_range: str | None,
) -> StatefulAxes:
    """Build StatefulAxes from CLI options."""
    kwargs: dict = {}
    if templates:
        kwargs["templates"] = [
            TemplateType(t.strip()) for t in templates.split(",")
        ]
    if predicate_types:
        kwargs["predicate_types"] = [
            PredicateType(p.strip()) for p in predicate_types.split(",")
        ]
    if transform_types:
        kwargs["transform_types"] = [
            TransformType(t.strip()) for t in transform_types.split(",")
        ]
    if value_range:
        kwargs["value_range"] = _parse_range(value_range)
    if threshold_range:
        kwargs["threshold_range"] = _parse_range(threshold_range)
    if divisor_range:
        kwargs["divisor_range"] = _parse_range(divisor_range)
    if list_length_range:
        kwargs["list_length_range"] = _parse_range(list_length_range)
    if shift_range:
        kwargs["shift_range"] = _parse_range(shift_range)
    if scale_range:
        kwargs["scale_range"] = _parse_range(scale_range)
    return StatefulAxes(**kwargs)


def _build_piecewise_axes(
    n_branches: int | None,
    expr_types: str | None,
    value_range: str | None,
    threshold_range: str | None,
    divisor_range: str | None,
    coeff_range: str | None,
) -> PiecewiseAxes:
    """Build PiecewiseAxes from CLI options."""
    kwargs: dict = {}
    if n_branches is not None:
        kwargs["n_branches"] = n_branches
    if expr_types:
        kwargs["expr_types"] = [
            ExprType(e.strip()) for e in expr_types.split(",")
        ]
    if value_range:
        kwargs["value_range"] = _parse_range(value_range)
    if threshold_range:
        kwargs["threshold_range"] = _parse_range(threshold_range)
    if divisor_range:
        kwargs["divisor_range"] = _parse_range(divisor_range)
    if coeff_range:
        kwargs["coeff_range"] = _parse_range(coeff_range)
    return PiecewiseAxes(**kwargs)


@app.command()
def generate(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output JSONL file")
    ],
    family: Annotated[
        str, typer.Option("--family", "-f", help="piecewise, stateful, or all")
    ] = "all",
    count: Annotated[
        int, typer.Option("--count", "-n", help="Number of tasks")
    ] = 100,
    seed: Annotated[
        int | None, typer.Option("--seed", "-s", help="Random seed")
    ] = None,
    # Type filters - stateful
    templates: Annotated[
        str | None,
        typer.Option(help="Stateful templates (comma-separated)"),
    ] = None,
    predicate_types: Annotated[
        str | None,
        typer.Option("--predicate-types", help="Predicate types"),
    ] = None,
    transform_types: Annotated[
        str | None,
        typer.Option("--transform-types", help="Transform types"),
    ] = None,
    # Type filters - piecewise
    n_branches: Annotated[
        int | None,
        typer.Option("--n-branches", help="Number of piecewise branches"),
    ] = None,
    expr_types: Annotated[
        str | None,
        typer.Option("--expr-types", help="Expression types (comma-separated)"),
    ] = None,
    # Range options - shared
    value_range: Annotated[
        str | None,
        typer.Option("--value-range", help="Value range (lo,hi)"),
    ] = None,
    threshold_range: Annotated[
        str | None,
        typer.Option("--threshold-range", help="Threshold range (lo,hi)"),
    ] = None,
    divisor_range: Annotated[
        str | None,
        typer.Option("--divisor-range", help="Divisor range (lo,hi)"),
    ] = None,
    # Range options - piecewise only
    coeff_range: Annotated[
        str | None,
        typer.Option("--coeff-range", help="Coefficient range (lo,hi)"),
    ] = None,
    # Range options - stateful only
    list_length_range: Annotated[
        str | None,
        typer.Option("--list-length-range", help="List length range (lo,hi)"),
    ] = None,
    shift_range: Annotated[
        str | None,
        typer.Option("--shift-range", help="Shift range (lo,hi)"),
    ] = None,
    scale_range: Annotated[
        str | None,
        typer.Option("--scale-range", help="Scale range (lo,hi)"),
    ] = None,
) -> None:
    """Generate tasks to JSONL file."""
    rng = random.Random(seed)
    tasks: list[Task] = []

    # Warn about mismatched options
    stateful_only = [
        templates,
        predicate_types,
        transform_types,
        list_length_range,
        shift_range,
        scale_range,
    ]
    piecewise_only = [n_branches, expr_types, coeff_range]

    if family == "piecewise" and any(opt is not None for opt in stateful_only):
        typer.echo(
            "Warning: stateful-only options ignored for piecewise family",
            err=True,
        )
    if family == "stateful" and any(opt is not None for opt in piecewise_only):
        typer.echo(
            "Warning: piecewise-only options ignored for stateful family",
            err=True,
        )

    # Build axes
    stateful_axes = _build_stateful_axes(
        templates=templates,
        predicate_types=predicate_types,
        transform_types=transform_types,
        value_range=value_range,
        threshold_range=threshold_range,
        divisor_range=divisor_range,
        list_length_range=list_length_range,
        shift_range=shift_range,
        scale_range=scale_range,
    )
    piecewise_axes = _build_piecewise_axes(
        n_branches=n_branches,
        expr_types=expr_types,
        value_range=value_range,
        threshold_range=threshold_range,
        divisor_range=divisor_range,
        coeff_range=coeff_range,
    )

    if family == "all":
        half = count // 2
        for _ in range(half):
            tasks.append(generate_piecewise_task(axes=piecewise_axes, rng=rng))
        for _ in range(count - half):
            tasks.append(generate_stateful_task(axes=stateful_axes, rng=rng))
    elif family == "piecewise":
        for _ in range(count):
            tasks.append(generate_piecewise_task(axes=piecewise_axes, rng=rng))
    elif family == "stateful":
        for _ in range(count):
            tasks.append(generate_stateful_task(axes=stateful_axes, rng=rng))
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
    # Random split options
    random_ratio: Annotated[
        float | None,
        typer.Option("--random-ratio", help="Train ratio (0-1)"),
    ] = None,
    split_seed: Annotated[
        int | None,
        typer.Option("--seed", help="Random seed for reproducibility"),
    ] = None,
    # Axis holdout options
    holdout_axis: Annotated[
        str | None,
        typer.Option("--holdout-axis", help="Dot-path to spec field"),
    ] = None,
    holdout_value: Annotated[
        str | None,
        typer.Option("--holdout-value", help="Value to hold out"),
    ] = None,
    holdout_type: Annotated[
        str, typer.Option("--holdout-type", help="exact, range, or contains")
    ] = "exact",
) -> None:
    """Split tasks using random split or axis holdouts."""
    raw = list(srsly.read_jsonl(input_file))
    tasks = [Task.model_validate(t) for t in raw]

    # Validate options
    has_random = random_ratio is not None
    has_holdout = holdout_axis is not None or holdout_value is not None

    if has_random and has_holdout:
        typer.echo(
            "Error: Cannot use both --random-ratio and holdout options",
            err=True,
        )
        raise typer.Exit(1)

    if not has_random and not has_holdout:
        typer.echo(
            "Error: Must provide --random-ratio or holdout options",
            err=True,
        )
        raise typer.Exit(1)

    if has_random:
        assert random_ratio is not None
        if random_ratio <= 0 or random_ratio >= 1:
            typer.echo(
                "Error: --random-ratio must be between 0 and 1", err=True
            )
            raise typer.Exit(1)
        result = random_split(tasks, random_ratio, seed=split_seed)
    else:
        if holdout_axis is None or holdout_value is None:
            typer.echo(
                "Error: Both --holdout-axis and --holdout-value are required",
                err=True,
            )
            raise typer.Exit(1)

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
    tasks = [Task.model_validate(t) for t in raw]

    by_family: dict[str, int] = {}
    for t in tasks:
        by_family[t.family] = by_family.get(t.family, 0) + 1

    typer.echo(f"{input_file}: {len(tasks)} tasks")
    for fam, cnt in sorted(by_family.items()):
        typer.echo(f"  {fam}: {cnt}")
