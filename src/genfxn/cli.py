import json
import random
from pathlib import Path
from typing import Annotated, Any, cast

import srsly
import typer
from pydantic import TypeAdapter

from genfxn.core.codegen import get_spec_value, task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.predicates import PredicateType
from genfxn.core.presets import get_difficulty_axes, get_valid_difficulties
from genfxn.core.string_predicates import StringPredicateType
from genfxn.core.string_transforms import StringTransformType
from genfxn.core.trace import GenerationTrace
from genfxn.core.transforms import TransformType
from genfxn.fsm.models import FsmAxes, FsmSpec
from genfxn.fsm.task import generate_fsm_task
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.piecewise.models import ExprType, PiecewiseAxes, PiecewiseSpec
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.simple_algorithms.models import (
    CountingMode,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)
from genfxn.simple_algorithms.models import (
    TemplateType as SimpleAlgoTemplateType,
)
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.splits import AxisHoldout, HoldoutType
from genfxn.stack_bytecode.models import (
    StackBytecodeAxes,
    StackBytecodeSpec,
)
from genfxn.stack_bytecode.queries import generate_stack_bytecode_queries
from genfxn.stack_bytecode.render import render_stack_bytecode
from genfxn.stack_bytecode.templates import stack_template_program
from genfxn.stateful.models import StatefulAxes, StatefulSpec, TemplateType
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.models import (
    OverlapLevel,
    StringRulesAxes,
    StringRulesSpec,
)
from genfxn.stringrules.task import generate_stringrules_task

app = typer.Typer(help="Generate and split function synthesis tasks.")
_stateful_spec_adapter = TypeAdapter(StatefulSpec)
_simple_algorithms_spec_adapter = TypeAdapter(SimpleAlgorithmsSpec)
_fsm_spec_adapter = TypeAdapter(FsmSpec)


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


def _iter_validated_tasks(input_file: Path):
    for raw in srsly.read_jsonl(input_file):
        yield Task.model_validate(raw)


def _write_task_line(handle, task: Task) -> None:
    handle.write(srsly.json_dumps(task.model_dump()))
    handle.write("\n")


def _matches_holdout(task: Task, holdout: AxisHoldout) -> bool:
    value = get_spec_value(task.spec, holdout.axis_path)
    if value is None:
        return False

    match holdout.holdout_type:
        case HoldoutType.EXACT:
            return value == holdout.holdout_value
        case HoldoutType.RANGE:
            lo, hi = holdout.holdout_value
            if not isinstance(value, int | float):
                return False
            return lo <= value <= hi
        case HoldoutType.CONTAINS:
            try:
                return holdout.holdout_value in value
            except TypeError:
                return False
    return False


def _count_nonempty_jsonl_lines(input_file: Path) -> int:
    count = 0
    with input_file.open("rb") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _parse_single_language(language: str) -> Language:
    tokens = [token.strip().lower() for token in language.split(",")]
    parsed = [token for token in tokens if token]
    if not parsed:
        raise typer.BadParameter(
            "Expected exactly one language value (python, java, or rust)."
        )
    if len(parsed) > 1:
        raise typer.BadParameter(
            "Expected exactly one language value (python, java, or rust); "
            "comma-separated values are not supported."
        )
    if parsed[0] == "all":
        raise typer.BadParameter(
            "Language 'all' is not supported. "
            "Choose one of: python, java, rust."
        )
    try:
        return Language(parsed[0])
    except ValueError as err:
        raise typer.BadParameter(
            f"Unknown language '{parsed[0]}'. "
            "Expected one of: python, java, rust."
        ) from err


def _render_task_for_language(task: Task, language: Language) -> Task:
    if language == Language.PYTHON:
        return task

    try:
        render_fn = get_render_fn(language, task.family)
    except (ImportError, ModuleNotFoundError, ValueError) as err:
        raise typer.BadParameter(
            f"Language '{language.value}' is not available for '{task.family}'."
        ) from err

    match task.family:
        case "piecewise":
            spec_obj = PiecewiseSpec.model_validate(task.spec, strict=True)
        case "stateful":
            spec_obj = _stateful_spec_adapter.validate_python(
                task.spec, strict=True
            )
        case "simple_algorithms":
            spec_obj = _simple_algorithms_spec_adapter.validate_python(
                task.spec, strict=True
            )
        case "stringrules":
            spec_obj = StringRulesSpec.model_validate(task.spec, strict=True)
        case "stack_bytecode":
            spec_obj = StackBytecodeSpec.model_validate(task.spec, strict=True)
        case "fsm":
            spec_obj = _fsm_spec_adapter.validate_python(
                task.spec, strict=True
            )
        case _:
            raise typer.BadParameter(f"Unknown family: {task.family}")

    rendered_code = render_fn(spec_obj, func_name="f")
    return task.model_copy(update={"code": rendered_code})


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


def _build_stack_bytecode_axes(
    value_range: str | None,
    list_length_range: str | None,
) -> StackBytecodeAxes:
    kwargs: dict[str, Any] = {}
    if value_range:
        kwargs["value_range"] = _parse_range(value_range)
    if list_length_range:
        kwargs["list_length_range"] = _parse_range(list_length_range)
    return StackBytecodeAxes(**kwargs)


def _build_fsm_axes(
    value_range: str | None,
    threshold_range: str | None,
    divisor_range: str | None,
) -> FsmAxes:
    kwargs: dict[str, Any] = {}
    if value_range:
        kwargs["value_range"] = _parse_range(value_range)
    if threshold_range:
        kwargs["threshold_range"] = _parse_range(threshold_range)
    if divisor_range:
        kwargs["divisor_range"] = _parse_range(divisor_range)
    return FsmAxes(**kwargs)


def _render_stack_bytecode(spec: StackBytecodeSpec) -> str:
    return render_stack_bytecode(spec)


def _build_stack_bytecode_task(
    axes: StackBytecodeAxes,
    rng: random.Random,
) -> Task:
    target = axes.target_difficulty or rng.randint(1, 5)
    program = stack_template_program(target, rng)
    max_steps = rng.randint(*axes.max_step_count_range)
    jump_mode = rng.choice(axes.jump_target_modes)
    input_mode = rng.choice(axes.input_modes)
    spec = StackBytecodeSpec(
        program=program,
        max_step_count=max_steps,
        jump_target_mode=jump_mode,
        input_mode=input_mode,
    )
    spec_dict = spec.model_dump()
    queries = generate_stack_bytecode_queries(spec, axes, rng)
    return Task(
        task_id=task_id_from_spec("stack_bytecode", spec_dict),
        family="stack_bytecode",
        spec=spec_dict,
        code=_render_stack_bytecode(spec),
        queries=queries,
        trace=GenerationTrace(family="stack_bytecode", steps=[]),
        axes=axes.model_dump(),
        difficulty=compute_difficulty("stack_bytecode", spec_dict),
        description=describe_task("stack_bytecode", spec_dict),
    )


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
            help=(
                "piecewise, stateful, simple_algorithms, stringrules, "
                "stack_bytecode, fsm, or all"
            ),
        ),
    ] = "all",
    count: Annotated[
        int, typer.Option("--count", "-n", help="Number of tasks")
    ] = 100,
    seed: Annotated[
        int | None, typer.Option("--seed", "-s", help="Random seed")
    ] = None,
    language: Annotated[
        str,
        typer.Option(
            "--language",
            "-l",
            help="Single language to render: python, java, or rust.",
        ),
    ] = "python",
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
    generated_count = 0
    try:
        selected_language = _parse_single_language(language)
    except typer.BadParameter as err:
        typer.echo(f"Error: {err}", err=True)
        raise typer.Exit(1) from err

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
        stack_bytecode_axes = _build_stack_bytecode_axes(
            value_range=value_range,
            list_length_range=list_length_range,
        )
        fsm_axes = _build_fsm_axes(
            value_range=value_range,
            threshold_range=threshold_range,
            divisor_range=divisor_range,
        )

    with output.open("w", encoding="utf-8") as output_handle:

        def emit(task: Task) -> None:
            nonlocal generated_count
            rendered_task = _render_task_for_language(task, selected_language)
            _write_task_line(output_handle, rendered_task)
            generated_count += 1

        if family == "all":
            # Split count as evenly as possible across all families.
            family_order = [
                "piecewise",
                "stateful",
                "simple_algorithms",
                "stringrules",
                "stack_bytecode",
                "fsm",
            ]
            base = count // len(family_order)
            remainder = count % len(family_order)
            family_counts = {
                fam: base + (1 if idx < remainder else 0)
                for idx, fam in enumerate(family_order)
            }

            for _ in range(family_counts["piecewise"]):
                emit(generate_piecewise_task(axes=piecewise_axes, rng=rng))
            for _ in range(family_counts["stateful"]):
                emit(generate_stateful_task(axes=stateful_axes, rng=rng))
            for _ in range(family_counts["simple_algorithms"]):
                emit(
                    generate_simple_algorithms_task(
                        axes=simple_algo_axes,
                        rng=rng,
                    )
                )
            for _ in range(family_counts["stringrules"]):
                emit(generate_stringrules_task(axes=stringrules_axes, rng=rng))
            for _ in range(family_counts["stack_bytecode"]):
                emit(_build_stack_bytecode_task(stack_bytecode_axes, rng))
            for _ in range(family_counts["fsm"]):
                emit(generate_fsm_task(axes=fsm_axes, rng=rng))
        elif family == "piecewise":
            for _ in range(count):
                if difficulty is not None:
                    axes = get_difficulty_axes(family, difficulty, variant, rng)
                else:
                    axes = piecewise_axes
                emit(
                    generate_piecewise_task(
                        axes=cast(PiecewiseAxes, axes),
                        rng=rng,
                    )
                )
        elif family == "stateful":
            for _ in range(count):
                if difficulty is not None:
                    axes = get_difficulty_axes(family, difficulty, variant, rng)
                else:
                    axes = stateful_axes
                emit(
                    generate_stateful_task(
                        axes=cast(StatefulAxes, axes),
                        rng=rng,
                    )
                )
        elif family == "simple_algorithms":
            for _ in range(count):
                if difficulty is not None:
                    axes = get_difficulty_axes(family, difficulty, variant, rng)
                else:
                    axes = simple_algo_axes
                emit(
                    generate_simple_algorithms_task(
                        axes=cast(SimpleAlgorithmsAxes, axes),
                        rng=rng,
                    )
                )
        elif family == "stringrules":
            for _ in range(count):
                if difficulty is not None:
                    axes = get_difficulty_axes(family, difficulty, variant, rng)
                else:
                    axes = stringrules_axes
                emit(
                    generate_stringrules_task(
                        axes=cast(StringRulesAxes, axes),
                        rng=rng,
                    )
                )
        elif family == "stack_bytecode":
            for _ in range(count):
                if difficulty is not None:
                    axes = get_difficulty_axes(family, difficulty, variant, rng)
                else:
                    axes = stack_bytecode_axes
                emit(
                    _build_stack_bytecode_task(
                        cast(StackBytecodeAxes, axes),
                        rng,
                    )
                )
        elif family == "fsm":
            for _ in range(count):
                if difficulty is not None:
                    axes = get_difficulty_axes(family, difficulty, variant, rng)
                else:
                    axes = fsm_axes
                emit(generate_fsm_task(axes=cast(FsmAxes, axes), rng=rng))
        else:
            typer.echo(f"Unknown family: {family}", err=True)
            raise typer.Exit(1)

    typer.echo(f"Generated {generated_count} tasks to {output}")


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
        HoldoutType,
        typer.Option("--holdout-type", help="exact, range, or contains"),
    ] = HoldoutType.EXACT,
) -> None:
    """Split tasks using random split or axis holdouts."""
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
        total_count = _count_nonempty_jsonl_lines(input_file)
        target_train_count = int(total_count * random_ratio)
        rng = random.Random(split_seed)
        with (
            train.open("w", encoding="utf-8") as train_handle,
            test.open("w", encoding="utf-8") as test_handle,
        ):
            remaining_total = total_count
            remaining_train = target_train_count
            train_count = 0
            test_count = 0
            for task in _iter_validated_tasks(input_file):
                if remaining_train == 0:
                    send_to_train = False
                elif remaining_train == remaining_total:
                    send_to_train = True
                else:
                    send_to_train = rng.random() < (
                        remaining_train / remaining_total
                    )

                if send_to_train:
                    _write_task_line(train_handle, task)
                    train_count += 1
                    remaining_train -= 1
                else:
                    _write_task_line(test_handle, task)
                    test_count += 1

                remaining_total -= 1
    else:
        if holdout_axis is None or holdout_value is None:
            typer.echo(
                "Error: Both --holdout-axis and --holdout-value are required",
                err=True,
            )
            raise typer.Exit(1)

        parsed_value: str | int | float | bool | None | tuple[int, int]
        if holdout_type == HoldoutType.RANGE:
            range_val = _parse_range(holdout_value)
            if range_val is None:
                typer.echo(
                    "Error: --holdout-value is required for range holdout",
                    err=True,
                )
                raise typer.Exit(1)
            parsed_value = range_val
        else:
            try:
                parsed_value = json.loads(holdout_value)
            except json.JSONDecodeError:
                parsed_value = holdout_value

        holdouts = [
            AxisHoldout(
                axis_path=holdout_axis,
                holdout_type=holdout_type,
                holdout_value=parsed_value,
            )
        ]
        total_count = 0
        train_count = 0
        test_count = 0
        first_sample: Any = None
        with (
            train.open("w", encoding="utf-8") as train_handle,
            test.open("w", encoding="utf-8") as test_handle,
        ):
            for task in _iter_validated_tasks(input_file):
                total_count += 1
                if first_sample is None:
                    first_sample = get_spec_value(task.spec, holdout_axis)
                if any(_matches_holdout(task, h) for h in holdouts):
                    _write_task_line(test_handle, task)
                    test_count += 1
                else:
                    _write_task_line(train_handle, task)
                    train_count += 1

        if test_count == 0 and total_count > 0:
            typer.echo(
                f"Warning: holdout matched 0 of {total_count} tasks. "
                f"Check --holdout-axis spelling (got '{holdout_axis}').",
                err=True,
            )
            typer.echo(
                f"  First task's value at '{holdout_axis}': {first_sample!r}",
                err=True,
            )

    typer.echo(f"Train: {train_count}, Test: {test_count}")


@app.command()
def info(
    input_file: Annotated[Path, typer.Argument(help="Input JSONL file")],
) -> None:
    """Show info about tasks file."""
    by_family: dict[str, int] = {}
    total = 0
    for t in _iter_validated_tasks(input_file):
        total += 1
        by_family[t.family] = by_family.get(t.family, 0) + 1

    typer.echo(f"{input_file}: {total} tasks")
    for fam, cnt in sorted(by_family.items()):
        typer.echo(f"  {fam}: {cnt}")
