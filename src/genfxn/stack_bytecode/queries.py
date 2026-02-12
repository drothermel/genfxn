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


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    lo, hi = bounds
    return min(max(value, lo), hi)


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

    # Coverage: min-length, an optional one-item case, and midpoint length.
    one_len = min(max(l_lo, 1), l_hi)
    coverage_lengths = [l_lo, one_len, (l_lo + l_hi) // 2]
    coverage_inputs = [
        _rand_list(length, axes.value_range, rng)
        for length in dict.fromkeys(coverage_lengths)
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

    # Adversarial: repeating patterns and zero-heavy vectors within bounds.
    adv_len = 0 if l_hi == 0 else min(max(l_lo, 1), l_hi)
    base_pattern = [0, 1, -1, 0, 1, -1]
    patterned = [
        _clamp(base_pattern[i % len(base_pattern)], axes.value_range)
        for i in range(adv_len)
    ]
    zeros = [_clamp(0, axes.value_range) for _ in range(adv_len)]
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

    deduped = dedupe_queries(queries)
    present_tags = {query.tag for query in deduped}
    if present_tags == set(QueryTag):
        return deduped

    len_lo, len_hi = axes.list_length_range
    value_span = max(1, v_hi - v_lo + 1)
    for missing_tag in QueryTag:
        if missing_tag in present_tags:
            continue
        for attempt in range(32):
            if len_hi == 0:
                candidate_input: list[int] = []
            else:
                length_span = max(1, len_hi - len_lo + 1)
                length = len_lo + (attempt % length_span)
                candidate_input = [
                    _clamp(
                        v_lo + ((attempt + i) % value_span),
                        axes.value_range,
                    )
                    for i in range(length)
                ]
            if any(existing.input == candidate_input for existing in deduped):
                continue
            deduped.append(
                Query(
                    input=candidate_input,
                    output=eval_stack_bytecode(spec, candidate_input),
                    tag=missing_tag,
                )
            )
            present_tags.add(missing_tag)
            break

    return deduped
