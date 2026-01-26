import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.stateful.models import StatefulAxes
from genfxn.stateful.queries import generate_stateful_queries
from genfxn.stateful.render import render_stateful
from genfxn.stateful.sampler import sample_stateful_spec


def generate_stateful_task(
    axes: StatefulAxes | None = None,
    rng: random.Random | None = None,
) -> Task:
    if axes is None:
        axes = StatefulAxes()
    if rng is None:
        rng = random.Random()

    spec = sample_stateful_spec(axes, rng)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("stateful", spec_dict)
    code = render_stateful(spec)
    queries = generate_stateful_queries(spec, axes, rng)

    return Task(
        task_id=task_id,
        family="stateful",
        spec=spec_dict,
        code=code,
        queries=queries,
    )
