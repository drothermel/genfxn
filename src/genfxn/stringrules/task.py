import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.stringrules.models import StringRulesAxes, StringRulesSpec
from genfxn.stringrules.queries import (
    StringRulesQueryGenerationError,
    generate_stringrules_queries,
)
from genfxn.stringrules.render import render_stringrules
from genfxn.stringrules.sampler import sample_stringrules_spec

_MAX_QUERY_GEN_RETRIES = 20


def _render_stringrules_for_languages(
    spec: StringRulesSpec,
    languages: list[Language] | None,
) -> str | dict[str, str]:
    if languages is None:
        return render_stringrules(spec)
    if len(languages) == 0:
        raise ValueError("languages list is empty")

    rendered: dict[str, str] = {}
    for language in dict.fromkeys(languages):
        render_fn = get_render_fn(language, "stringrules")
        rendered[language.value] = render_fn(spec, func_name="f")
    return rendered


def generate_stringrules_task(
    axes: StringRulesAxes | None = None,
    rng: random.Random | None = None,
    languages: list[Language] | None = None,
) -> Task:
    if axes is None:
        axes = StringRulesAxes()
    if rng is None:
        rng = random.Random()

    last_error: StringRulesQueryGenerationError | None = None
    for _ in range(_MAX_QUERY_GEN_RETRIES):
        trace_steps: list[TraceStep] = []
        spec = sample_stringrules_spec(axes, rng, trace=trace_steps)
        try:
            queries = generate_stringrules_queries(spec, axes, rng)
        except StringRulesQueryGenerationError as exc:
            last_error = exc
            continue

        spec_dict = spec.model_dump()
        task_id = task_id_from_spec("stringrules", spec_dict)
        code = _render_stringrules_for_languages(spec, languages)
        trace = GenerationTrace(family="stringrules", steps=trace_steps)

        return Task(
            task_id=task_id,
            family="stringrules",
            spec=spec_dict,
            code=code,
            queries=queries,
            trace=trace,
            axes=axes.model_dump(),
            difficulty=compute_difficulty("stringrules", spec_dict),
            description=describe_task("stringrules", spec_dict),
        )

    message = (
        "failed to generate replace-aware stringrules queries after "
        f"{_MAX_QUERY_GEN_RETRIES} attempts"
    )
    if last_error is not None:
        raise RuntimeError(f"{message}: {last_error}") from last_error
    raise RuntimeError(message)
