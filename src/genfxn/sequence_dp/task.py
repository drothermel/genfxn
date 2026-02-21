import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.sequence_dp.models import (
    SequenceDpAxes,
    SequenceDpSpec,
)
from genfxn.sequence_dp.queries import generate_sequence_dp_queries
from genfxn.sequence_dp.render import render_sequence_dp
from genfxn.sequence_dp.sampler import sample_sequence_dp_spec


def _render_sequence_dp_for_languages(
    spec: SequenceDpSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_sequence_dp(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "sequence_dp")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_sequence_dp_task(
    axes: SequenceDpAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = SequenceDpAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_sequence_dp_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()

    return Task(
        task_id=task_id_from_spec("sequence_dp", spec_dict),
        family="sequence_dp",
        spec=spec_dict,
        code=_render_sequence_dp_for_languages(spec, languages),
        queries=generate_sequence_dp_queries(spec, axes, rng),
        trace=GenerationTrace(family="sequence_dp", steps=trace_steps),
        axes=axes.model_dump(),
        description=describe_task("sequence_dp", spec_dict),
    )
