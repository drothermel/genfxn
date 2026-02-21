import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.graph_queries.models import GraphQueriesAxes, GraphQueriesSpec
from genfxn.graph_queries.queries import generate_graph_queries_queries
from genfxn.graph_queries.render import render_graph_queries
from genfxn.graph_queries.sampler import sample_graph_queries_spec
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language


def _render_graph_queries_for_languages(
    spec: GraphQueriesSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_graph_queries(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "graph_queries")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_graph_queries_task(
    axes: GraphQueriesAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = GraphQueriesAxes()
    if rng is None:
        rng = random.Random()  # noqa: S311

    trace_steps: list[TraceStep] = []
    spec = sample_graph_queries_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()

    return Task(
        task_id=task_id_from_spec("graph_queries", spec_dict),
        family="graph_queries",
        spec=spec_dict,
        code=_render_graph_queries_for_languages(spec, languages),
        queries=generate_graph_queries_queries(spec, axes, rng),
        trace=GenerationTrace(family="graph_queries", steps=trace_steps),
        axes=axes.model_dump(),
        description=describe_task("graph_queries", spec_dict),
    )
