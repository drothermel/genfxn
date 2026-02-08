import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.render import render_all_languages
from genfxn.langs.types import Language
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.piecewise.queries import generate_piecewise_queries
from genfxn.piecewise.sampler import sample_piecewise_spec


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
    code = render_all_languages("piecewise", spec, languages)
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
