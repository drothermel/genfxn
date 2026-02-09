import random

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.trace import GenerationTrace, TraceStep
from genfxn.sequence_dp.models import SequenceDpAxes, SequenceDpSpec
from genfxn.sequence_dp.queries import generate_sequence_dp_queries
from genfxn.sequence_dp.render import render_sequence_dp
from genfxn.sequence_dp.sampler import sample_sequence_dp_spec


def _describe_sequence_dp(spec: SequenceDpSpec) -> str:
    predicate = spec.match_predicate

    if predicate.kind == "eq":
        predicate_text = "elements are equal"
    elif predicate.kind == "abs_diff_le":
        predicate_text = (
            f"absolute difference is <= {predicate.max_diff}"
        )
    else:
        predicate_text = (
            "modulo-difference satisfies "
            f"(a-b) % {predicate.divisor} == {predicate.remainder}"
        )

    return (
        "Compute a sequence dynamic-programming score over two integer lists "
        f"using {spec.template.value} semantics. "
        f"A pair matches when {predicate_text}. "
        f"Use match={spec.match_score}, mismatch={spec.mismatch_score}, "
        f"gap={spec.gap_score}, and tie-break={spec.step_tie_break.value}. "
        f"Return {spec.output_mode.value}."
    )


def generate_sequence_dp_task(
    axes: SequenceDpAxes | None = None,
    rng: random.Random | None = None,
    languages: list[str] | None = None,
) -> Task:
    if languages is not None:
        raise ValueError("languages not yet supported for sequence_dp")

    if axes is None:
        axes = SequenceDpAxes()
    if rng is None:
        rng = random.Random()

    trace_steps: list[TraceStep] = []
    spec = sample_sequence_dp_spec(axes, rng, trace=trace_steps)
    spec_dict = spec.model_dump()
    difficulty = compute_difficulty("sequence_dp", spec_dict)

    return Task(
        task_id=task_id_from_spec("sequence_dp", spec_dict),
        family="sequence_dp",
        spec=spec_dict,
        code=render_sequence_dp(spec),
        queries=generate_sequence_dp_queries(spec, axes, rng),
        trace=GenerationTrace(family="sequence_dp", steps=trace_steps),
        axes=axes.model_dump(),
        difficulty=difficulty,
        description=_describe_sequence_dp(spec),
    )
