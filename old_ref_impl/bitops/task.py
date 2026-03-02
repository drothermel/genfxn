import random

from genfxn.bitops.models import BitopsAxes, BitopsSpec
from genfxn.bitops.queries import generate_bitops_queries
from genfxn.bitops.render import render_bitops
from genfxn.bitops.sampler import sample_bitops_spec
from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.models import Task
from genfxn.core.task_ids import compute_task_ids
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language


def _render_bitops_for_languages(
    spec: BitopsSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_bitops(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "bitops")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_bitops_task(
    axes: BitopsAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = BitopsAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_bitops_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    code = _render_bitops_for_languages(spec, languages)
    ids = compute_task_ids("bitops", spec_dict, code)

    description = describe_task("bitops", spec_dict)

    return Task(
        task_id=task_id_from_spec("bitops", spec_dict),
        spec_id=ids.spec_id,
        sem_hash=ids.sem_hash,
        ast_id=ids.ast_id,
        family="bitops",
        spec=spec_dict,
        code=code,
        queries=generate_bitops_queries(spec, axes, rng),
        trace=GenerationTrace(family="bitops", steps=trace_steps),
        axes=axes.model_dump(),
        description=description,
    )
