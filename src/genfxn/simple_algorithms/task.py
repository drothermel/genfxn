import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.simple_algorithms.queries import generate_simple_algorithms_queries
from genfxn.simple_algorithms.render import render_simple_algorithms
from genfxn.simple_algorithms.sampler import sample_simple_algorithms_spec


def generate_simple_algorithms_task(
    axes: SimpleAlgorithmsAxes | None = None,
    rng: random.Random | None = None,
) -> Task:
    if axes is None:
        axes = SimpleAlgorithmsAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_simple_algorithms_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("simple_algorithms", spec_dict)
    code = render_simple_algorithms(spec)
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
    )
