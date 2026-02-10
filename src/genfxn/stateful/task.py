import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.stateful.models import StatefulAxes, StatefulSpec
from genfxn.stateful.queries import generate_stateful_queries
from genfxn.stateful.render import render_stateful
from genfxn.stateful.sampler import sample_stateful_spec


def _render_stateful_for_languages(
    spec: StatefulSpec,
    languages: list[Language] | None,
    *,
    no_i32_wrap: bool = False,
) -> str | dict[str, str]:
    if languages is None:
        return render_stateful(spec, int32_wrap=not no_i32_wrap)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "stateful")
        if language == Language.PYTHON:
            rendered[language.value] = render_fn(
                spec,
                func_name="f",
                int32_wrap=not no_i32_wrap,
            )
        else:
            rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_stateful_task(
    axes: StatefulAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
    *,
    no_i32_wrap: bool = False,
) -> Task:
    if axes is None:
        axes = StatefulAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_stateful_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("stateful", spec_dict)
    code = _render_stateful_for_languages(
        spec,
        languages,
        no_i32_wrap=no_i32_wrap,
    )
    queries = generate_stateful_queries(
        spec,
        axes,
        rng,
        int32_wrap=not no_i32_wrap,
    )

    trace = GenerationTrace(family="stateful", steps=trace_steps)
    difficulty = compute_difficulty("stateful", spec_dict)
    description = describe_task("stateful", spec_dict)

    return Task(
        task_id=task_id,
        family="stateful",
        spec=spec_dict,
        code=code,
        queries=queries,
        trace=trace,
        axes=axes.model_dump(),
        difficulty=difficulty,
        description=description,
    )
