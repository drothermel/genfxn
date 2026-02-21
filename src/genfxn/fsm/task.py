import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.fsm.models import FsmAxes, FsmSpec
from genfxn.fsm.queries import generate_fsm_queries
from genfxn.fsm.render import render_fsm
from genfxn.fsm.sampler import sample_fsm_spec
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language


def _render_fsm_for_languages(
    spec: FsmSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_fsm(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "fsm")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_fsm_task(
    axes: FsmAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = FsmAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_fsm_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()

    return Task(
        task_id=task_id_from_spec("fsm", spec_dict),
        family="fsm",
        spec=spec_dict,
        code=_render_fsm_for_languages(spec, languages),
        queries=generate_fsm_queries(spec, axes, rng),
        trace=GenerationTrace(family="fsm", steps=trace_steps),
        axes=axes.model_dump(),
        description=describe_task("fsm", spec_dict),
    )
