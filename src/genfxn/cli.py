import random
from pathlib import Path
from typing import Annotated, cast

import srsly
import typer

from genfxn.core.codegen import get_spec_value
from genfxn.core.models import Task
from genfxn.core.predicates import PredicateType
from genfxn.core.presets import get_difficulty_axes, get_valid_difficulties
from genfxn.core.string_predicates import StringPredicateType
from genfxn.core.string_transforms import StringTransformType
from genfxn.core.transforms import TransformType
from genfxn.piecewise.models import ExprType, PiecewiseAxes
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.simple_algorithms.models import (
    CountingMode,
    SimpleAlgorithmsAxes,
    TieBreakMode,
)
from genfxn.simple_algorithms.models import (
    TemplateType as SimpleAlgoTemplateType,
)
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.splits import AxisHoldout, HoldoutType, random_split, split_tasks
from genfxn.stateful.models import StatefulAxes, TemplateType
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.models import OverlapLevel, StringRulesAxes
from genfxn.stringrules.task import generate_stringrules_task

app = typer.Typer(help="Generate and split function synthesis tasks.")


def _parse_range(value: str | None) -> tuple[int, int] | None:
    """Parse 'lo,hi' into tuple. Raises typer.BadParameter on invalid input."""
    if value is None:
        return None
    try:
        parts = value.split(",")
        if len(parts) != 2:
            raise typer.BadParameter(
                f"Invalid range '{value}': expected 'LO,HI' (e.g., '5,10')"
            )
        lo_s, hi_s = parts[0].strip(), parts[1].strip()
        if not lo_s or not hi_s:
            raise typer.BadParameter(
                f"Invalid range '{value}': expected 'LO,HI' (e.g., '5,10')"
            )
        lo = int(lo_s)
        hi = int(hi_s)
        if lo > hi:
            raise typer.BadParameter(
                f"Invalid range '{value}': low must be <= high"
            )
        return (lo, hi)
    except (ValueError, IndexError) as err:
        raise typer.BadParameter(
            f"Invalid range '{value}': expected 'LO,HI' (e.g., '5,10')"
        ) from err


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
        tokens = [p.strip() for p in predicate_types.split(",")]
        if any(t.lower() == "in_set" for t in tokens):
            typer.echo(
                "IN_SET is not supported for stateful generation",
                err=True,
            )
            raise typer.Exit(1)
        parsed_predicate_types = [PredicateType(t) for t in tokens]
        kwargs["predicate_types"] = parsed_predicate_types
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


def _build_simple_algorithms_axes(
    algorithm_types: str | None,
    tie_break_modes: str | None,
    counting_modes: str | None,
    window_size_range: str | None,
    target_range: str | None,
    value_range: str | None,
    list_length_range: str | None,
) -> SimpleAlgorithmsAxes:
    """Build SimpleAlgorithmsAxes from CLI options."""
    kwargs: dict = {}
    if algorithm_types:
        kwargs["templates"] = [
            SimpleAlgoTemplateType(t.strip())
            for t in algorithm_types.split(",")
        ]
    if tie_break_modes:
        kwargs["tie_break_modes"] = [
            TieBreakMode(m.strip()) for m in tie_break_modes.split(",")
        ]
    if counting_modes:
        kwargs["counting_modes"] = [
            CountingMode(m.strip()) for m in counting_modes.split(",")
        ]
    if window_size_range:
        kwargs["window_size_range"] = _parse_range(window_size_range)
    if target_range:
        kwargs["target_range"] = _parse_range(target_range)
    if value_range:
        kwargs["value_range"] = _parse_range(value_range)
    if list_length_range:
        kwargs["list_length_range"] = _parse_range(list_length_range)
    return SimpleAlgorithmsAxes(**kwargs)


def _build_stringrules_axes(
    n_rules: int | None,
    string_predicate_types: str | None,
    string_transform_types: str | None,
    overlap_level: str | None,
    string_length_range: str | None,
) -> StringRulesAxes:
    """Build StringRulesAxes from CLI options."""
    kwargs: dict = {}
    if n_rules is not None:
        kwargs["n_rules"] = n_rules
    if string_predicate_types:
        kwargs["predicate_types"] = [
            StringPredicateType(p.strip())
            for p in string_predicate_types.split(",")
        ]
    if string_transform_types:
        kwargs["transform_types"] = [
            StringTransformType(t.strip())
            for t in string_transform_types.split(",")
        ]
    if overlap_level:
        kwargs["overlap_level"] = OverlapLevel(overlap_level.strip())
    if string_length_range:
        kwargs["string_length_range"] = _parse_range(string_length_range)
    return StringRulesAxes(**kwargs)


@app.command()
def generate(
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Output JSONL file")
    ],
    family: Annotated[
        str,
        typer.Option(
            "--family",
            "-f",
            help="piecewise, stateful, simple_algorithms, stringrules, or all",
        ),
    ] = "all",
    count: Annotated[
        int, typer.Option("--count", "-n", help="Number of tasks")
    ] = 100,
    seed: Annotated[
        int | None, typer.Option("--seed", "-s", help="Random seed")
    ] = None,
    # Difficulty presets
    difficulty: Annotated[
        int | None,
        typer.Option(
            "--difficulty",
            "-d",
            help="Target difficulty level (1-5, depends on family)",
        ),
    ] = None,
    variant: Annotated[
        str | None,
        typer.Option(
            "--variant",
            help="Preset variant (e.g. '3A', '3B'). Random if omitted.",
        ),
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
    # Type filters - simple_algorithms
    algorithm_types: Annotated[
        str | None,
        typer.Option(
            "--algorithm-types",
            help="Algorithm types: most_frequent, count_pairs_sum, etc.",
        ),
    ] = None,
    tie_break_modes: Annotated[
        str | None,
        typer.Option("--tie-break-modes", help="smallest, first_seen"),
    ] = None,
    counting_modes: Annotated[
        str | None,
        typer.Option(
            "--counting-modes", help="Counting: all_indices, unique_values"
        ),
    ] = None,
    window_size_range: Annotated[
        str | None,
        typer.Option("--window-size-range", help="Window size range (lo,hi)"),
    ] = None,
    target_range: Annotated[
        str | None,
        typer.Option("--target-range", help="Target sum range (lo,hi)"),
    ] = None,
    # Type filters - stringrules
    n_rules: Annotated[
        int | None,
        typer.Option("--n-rules", help="Number of string rules (1-10)"),
    ] = None,
    string_predicate_types: Annotated[
        str | None,
        typer.Option(
            "--string-predicate-types",
            help="Predicate types: starts_with, ends_with, etc.",
        ),
    ] = None,
    string_transform_types: Annotated[
        str | None,
        typer.Option(
            "--string-transform-types",
            help="String transform types: lowercase, uppercase, reverse, etc.",
        ),
    ] = None,
    overlap_level: Annotated[
        str | None,
        typer.Option("--overlap-level", help="Overlap level: none, low, high"),
    ] = None,
    string_length_range: Annotated[
        str | None,
        typer.Option("--string-length-range", help="String length (lo,hi)"),
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

    # Validate difficulty/variant options
    if difficulty is not None:
        if family == "all":
            typer.echo(
                "Error: --difficulty requires a specific family, not 'all'",
                err=True,
            )
            raise typer.Exit(1)
        try:
            valid = get_valid_difficulties(family)
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from e
        if difficulty not in valid:
            typer.echo(
                f"Error: Invalid difficulty {difficulty} for {family}. "
                f"Valid: {valid}",
                err=True,
            )
            raise typer.Exit(1)

    if variant is not None and difficulty is None:
        typer.echo(
            "Error: --variant requires --difficulty to be specified",
            err=True,
        )
        raise typer.Exit(1)

    # Reject combining --difficulty presets with manual axes options
    if difficulty is not None:
        manual_axes = {
            "templates": templates,
            "predicate-types": predicate_types,
            "transform-types": transform_types,
            "value-range": value_range,
            "threshold-range": threshold_range,
            "divisor-range": divisor_range,
            "list-length-range": list_length_range,
            "shift-range": shift_range,
            "scale-range": scale_range,
            "expr-types": expr_types,
            "coeff-range": coeff_range,
            "n-branches": n_branches,
            "target-range": target_range,
            "window-size-range": window_size_range,
            "n-rules": n_rules,
            "string-predicate-types": string_predicate_types,
            "string-transform-types": string_transform_types,
            "overlap-level": overlap_level,
            "string-length-range": string_length_range,
            "algorithm-types": algorithm_types,
            "tie-break-modes": tie_break_modes,
            "counting-modes": counting_modes,
        }
        provided = [f"--{k}" for k, v in manual_axes.items() if v is not None]
        if provided:
            typer.echo(
                f"Error: --difficulty uses presets and cannot be combined "
                f"with manual axes options: {', '.join(provided)}",
                err=True,
            )
            raise typer.Exit(1)

    # Build axes for all families (or use preset if difficulty specified)
    if difficulty is not None:
        # Use difficulty preset - generate axes per task for variety
        pass  # Will build axes in the generation loop
    else:
        # Build static axes from CLI options
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
        simple_algo_axes = _build_simple_algorithms_axes(
            algorithm_types=algorithm_types,
            tie_break_modes=tie_break_modes,
            counting_modes=counting_modes,
            window_size_range=window_size_range,
            target_range=target_range,
            value_range=value_range,
            list_length_range=list_length_range,
        )
        stringrules_axes = _build_stringrules_axes(
            n_rules=n_rules,
            string_predicate_types=string_predicate_types,
            string_transform_types=string_transform_types,
            overlap_level=overlap_level,
            string_length_range=string_length_range,
        )

    if family == "all":
        # Split evenly among all 4 families
        quarter = count // 4
        for _ in range(quarter):
            tasks.append(generate_piecewise_task(axes=piecewise_axes, rng=rng))
        for _ in range(quarter):
            tasks.append(generate_stateful_task(axes=stateful_axes, rng=rng))
        for _ in range(quarter):
            t = generate_simple_algorithms_task(axes=simple_algo_axes, rng=rng)
            tasks.append(t)
        # Remainder goes to stringrules
        for _ in range(count - 3 * quarter):
            task = generate_stringrules_task(axes=stringrules_axes, rng=rng)
            tasks.append(task)
    elif family == "piecewise":
        for _ in range(count):
            if difficulty is not None:
                axes = get_difficulty_axes(family, difficulty, variant, rng)
            else:
                axes = piecewise_axes
            tasks.append(
                generate_piecewise_task(axes=cast(PiecewiseAxes, axes), rng=rng)
            )
    elif family == "stateful":
        for _ in range(count):
            if difficulty is not None:
                axes = get_difficulty_axes(family, difficulty, variant, rng)
            else:
                axes = stateful_axes
            tasks.append(
                generate_stateful_task(axes=cast(StatefulAxes, axes), rng=rng)
            )
    elif family == "simple_algorithms":
        for _ in range(count):
            if difficulty is not None:
                axes = get_difficulty_axes(family, difficulty, variant, rng)
            else:
                axes = simple_algo_axes
            t = generate_simple_algorithms_task(
                axes=cast(SimpleAlgorithmsAxes, axes), rng=rng
            )
            tasks.append(t)
    elif family == "stringrules":
        for _ in range(count):
            if difficulty is not None:
                axes = get_difficulty_axes(family, difficulty, variant, rng)
            else:
                axes = stringrules_axes
            task = generate_stringrules_task(
                axes=cast(StringRulesAxes, axes), rng=rng
            )
            tasks.append(task)
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
        typer.Option("--random-ratio", help="Train ratio in [0, 1]"),
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
        if random_ratio is None:
            typer.echo(
                "Error: --random-ratio is required for random split", err=True
            )
            raise typer.Exit(1)
        if random_ratio < 0 or random_ratio > 1:
            typer.echo("Error: --random-ratio must be in [0, 1]", err=True)
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
            range_val = _parse_range(holdout_value)
            if range_val is None:
                typer.echo(
                    "Error: --holdout-value is required for range holdout",
                    err=True,
                )
                raise typer.Exit(1)
            parsed_value = range_val

        holdouts = [
            AxisHoldout(
                axis_path=holdout_axis,
                holdout_type=HoldoutType(holdout_type),
                holdout_value=parsed_value,
            )
        ]
        result = split_tasks(tasks, holdouts)

    if result.holdouts and len(result.test) == 0 and tasks:
        typer.echo(
            f"Warning: holdout matched 0 of {len(tasks)} tasks. "
            f"Check --holdout-axis spelling (got '{holdout_axis}').",
            err=True,
        )
        sample_val = get_spec_value(tasks[0].spec, holdout_axis)
        typer.echo(
            f"  First task's value at '{holdout_axis}': {sample_val!r}",
            err=True,
        )

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
