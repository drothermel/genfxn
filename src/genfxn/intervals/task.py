import random
from typing import Any

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.intervals.models import IntervalsAxes, IntervalsSpec
from genfxn.intervals.queries import generate_intervals_queries
from genfxn.intervals.render import render_intervals
from genfxn.intervals.sampler import sample_intervals_spec
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language


def _local_description(spec_dict: dict[str, Any]) -> str:
    operation = spec_dict.get("operation", "total_coverage")
    boundary_mode = spec_dict.get("boundary_mode", "closed_closed")
    merge_touching = spec_dict.get("merge_touching", True)

    op_text = getattr(operation, "value", operation)
    boundary_text = getattr(boundary_mode, "value", boundary_mode)
    return (
        "Given integer intervals, normalize reversed endpoints, apply "
        f"{boundary_text} boundaries, merge touching={merge_touching}, and "
        f"return {op_text}."
    )


def _render_intervals_for_languages(
    spec: IntervalsSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_intervals(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "intervals")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_intervals_task(
    axes: IntervalsAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = IntervalsAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_intervals_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    difficulty = compute_difficulty("intervals", spec_dict)

    try:
        description = describe_task("intervals", spec_dict)
    except ValueError:
        description = _local_description(spec_dict)
    if not description:
        description = _local_description(spec_dict)

    return Task(
        task_id=task_id_from_spec("intervals", spec_dict),
        family="intervals",
        spec=spec_dict,
        code=_render_intervals_for_languages(spec, languages),
        queries=generate_intervals_queries(spec, axes, rng),
        trace=GenerationTrace(family="intervals", steps=trace_steps),
        axes=axes.model_dump(),
        difficulty=difficulty,
        description=description,
    )
