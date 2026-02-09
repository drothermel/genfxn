import random

from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.stack_bytecode.eval import eval_stack_bytecode
from genfxn.stack_bytecode.models import StackBytecodeAxes, StackBytecodeSpec


def _rand_list(
    length: int,
    value_range: tuple[int, int],
    rng: random.Random,
) -> list[int]:
    lo, hi = value_range
    return [rng.randint(lo, hi) for _ in range(length)]


def generate_stack_bytecode_queries(
    spec: StackBytecodeSpec,
    axes: StackBytecodeAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    v_lo, v_hi = axes.value_range
    l_lo, l_hi = axes.list_length_range

    queries: list[Query] = []

    # Coverage: empty, single, typical.
    coverage_inputs = [
        [],
        [rng.randint(v_lo, v_hi)],
        _rand_list((l_lo + l_hi) // 2, axes.value_range, rng),
    ]
    for xs in coverage_inputs:
        queries.append(
            Query(
                input=xs,
                output=eval_stack_bytecode(spec, xs),
                tag=QueryTag.COVERAGE,
            )
        )

    # Boundary: min/max values and min/max lengths.
    for length in {l_lo, l_hi}:
        if length < 0:
            continue
        mins = [v_lo for _ in range(length)]
        maxs = [v_hi for _ in range(length)]
        queries.append(
            Query(
                input=mins,
                output=eval_stack_bytecode(spec, mins),
                tag=QueryTag.BOUNDARY,
            )
        )
        queries.append(
            Query(
                input=maxs,
                output=eval_stack_bytecode(spec, maxs),
                tag=QueryTag.BOUNDARY,
            )
        )

    # Typical random inputs.
    for _ in range(4):
        length = rng.randint(l_lo, l_hi)
        xs = _rand_list(length, axes.value_range, rng)
        queries.append(
            Query(
                input=xs,
                output=eval_stack_bytecode(spec, xs),
                tag=QueryTag.TYPICAL,
            )
        )

    # Adversarial: repeating patterns and zero-heavy vectors.
    patterned = [0, 1, -1, 0, 1, -1][: max(0, min(l_hi, 6))]
    zeros = [0 for _ in range(max(0, min(l_hi, 6)))]
    queries.append(
        Query(
            input=patterned,
            output=eval_stack_bytecode(spec, patterned),
            tag=QueryTag.ADVERSARIAL,
        )
    )
    queries.append(
        Query(
            input=zeros,
            output=eval_stack_bytecode(spec, zeros),
            tag=QueryTag.ADVERSARIAL,
        )
    )

    return dedupe_queries(queries)
