import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.stack_bytecode.models import StackBytecodeAxes, StackBytecodeSpec
from genfxn.stack_bytecode.queries import generate_stack_bytecode_queries
from genfxn.stack_bytecode.render import render_stack_bytecode
from genfxn.stack_bytecode.sampler import sample_stack_bytecode_spec


def _render_stack_bytecode_for_languages(
    spec: StackBytecodeSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_stack_bytecode(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "stack_bytecode")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_stack_bytecode_task(
    axes: StackBytecodeAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = StackBytecodeAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_stack_bytecode_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    task_id = task_id_from_spec("stack_bytecode", spec_dict)
    code = _render_stack_bytecode_for_languages(spec, languages)
    queries = generate_stack_bytecode_queries(spec, axes, rng)
    description = describe_task("stack_bytecode", spec_dict)

    return Task(
        task_id=task_id,
        family="stack_bytecode",
        spec=spec_dict,
        code=code,
        queries=queries,
        trace=GenerationTrace(family="stack_bytecode", steps=trace_steps),
        axes=axes.model_dump(),
        description=description,
    )
