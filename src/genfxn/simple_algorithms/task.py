import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.render import render_all_languages
from genfxn.langs.types import Language
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.simple_algorithms.queries import generate_simple_algorithms_queries
from genfxn.simple_algorithms.sampler import sample_simple_algorithms_spec


def generate_simple_algorithms_task(
    axes: SimpleAlgorithmsAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = SimpleAlgorithmsAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_simple_algorithms_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("simple_algorithms", spec_dict)
    code = render_all_languages("simple_algorithms", spec, languages)
    queries = generate_simple_algorithms_queries(spec, axes, rng)

    trace = GenerationTrace(family="simple_algorithms", steps=trace_steps)

    return Task(
        task_id=task_id,
        family="simple_algorithms",
        spec=spec_dict,
        code=code,
        queries=queries,
        trace=trace,
        axes=axes.model_dump(),
        difficulty=compute_difficulty("simple_algorithms", spec_dict),
        description=describe_task("simple_algorithms", spec_dict),
    )
