import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.piecewise.models import PiecewiseAxes, PiecewiseSpec
from genfxn.piecewise.queries import generate_piecewise_queries
from genfxn.piecewise.render import render_piecewise
from genfxn.piecewise.sampler import sample_piecewise_spec


def _render_piecewise_for_languages(
    spec: PiecewiseSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_piecewise(spec)

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "piecewise")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_piecewise_task(
    axes: PiecewiseAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = PiecewiseAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_piecewise_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("piecewise", spec_dict)
    code = _render_piecewise_for_languages(spec, languages)
    queries = generate_piecewise_queries(spec, axes.value_range, rng)

    trace = GenerationTrace(family="piecewise", steps=trace_steps)
    difficulty = compute_difficulty("piecewise", spec_dict)
    description = describe_task("piecewise", spec_dict)

    return Task(
        task_id=task_id,
        family="piecewise",
        spec=spec_dict,
        code=code,
        queries=queries,
        trace=trace,
        axes=axes.model_dump(),
        difficulty=difficulty,
        description=description,
    )
