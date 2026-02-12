import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.temporal_logic.models import TemporalLogicAxes, TemporalLogicSpec
from genfxn.temporal_logic.queries import generate_temporal_logic_queries
from genfxn.temporal_logic.render import render_temporal_logic
from genfxn.temporal_logic.sampler import sample_temporal_logic_spec


def _render_temporal_logic_for_languages(
    spec: TemporalLogicSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_temporal_logic(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "temporal_logic")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_temporal_logic_task(
    axes: TemporalLogicAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = TemporalLogicAxes()
    if rng is None:
        rng = random.Random()  # noqa: S311

    trace_steps: list[TraceStep] = []
    spec = sample_temporal_logic_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    difficulty = compute_difficulty("temporal_logic", spec_dict)

    return Task(
        task_id=task_id_from_spec("temporal_logic", spec_dict),
        family="temporal_logic",
        spec=spec_dict,
        code=_render_temporal_logic_for_languages(spec, languages),
        queries=generate_temporal_logic_queries(spec, axes, rng),
        trace=GenerationTrace(family="temporal_logic", steps=trace_steps),
        axes=axes.model_dump(),
        difficulty=difficulty,
        description=describe_task("temporal_logic", spec_dict),
    )
