import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.piecewise.queries import generate_piecewise_queries
from genfxn.piecewise.render import render_piecewise
from genfxn.piecewise.sampler import sample_piecewise_spec


def generate_piecewise_task(
    axes: PiecewiseAxes | None = None,
    rng: random.Random | None = None,
) -> Task:
    if axes is None:
        axes = PiecewiseAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_piecewise_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("piecewise", spec_dict)
    code = render_piecewise(spec)
    queries = generate_piecewise_queries(spec, axes.value_range, rng)

    trace = GenerationTrace(family="piecewise", steps=trace_steps)

    return Task(
        task_id=task_id,
        family="piecewise",
        spec=spec_dict,
        code=code,
        queries=queries,
        trace=trace,
        axes=axes.model_dump(),
    )
