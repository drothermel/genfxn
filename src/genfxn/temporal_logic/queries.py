import random

from genfxn.core.models import Query, QueryTag
from genfxn.temporal_logic.eval import eval_temporal_logic
from genfxn.temporal_logic.models import TemporalLogicAxes, TemporalLogicSpec


def _append_query(
    queries: list[Query],
    spec: TemporalLogicSpec,
    xs: list[int],
    tag: QueryTag,
) -> None:
    normalized = [int(value) for value in xs]
    queries.append(
        Query(
            input=normalized,
            output=eval_temporal_logic(spec, normalized),
            tag=tag,
        )
    )


def _sample_sequence(
    *,
    length_range: tuple[int, int],
    value_range: tuple[int, int],
    rng: random.Random,
) -> list[int]:
    n = rng.randint(length_range[0], length_range[1])
    return [rng.randint(value_range[0], value_range[1]) for _ in range(n)]


def generate_temporal_logic_queries(
    spec: TemporalLogicSpec,
    axes: TemporalLogicAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()  # noqa: S311

    v_lo, v_hi = axes.value_range
    mid = (v_lo + v_hi) // 2
    queries: list[Query] = []

    coverage_cases = [
        [mid - 1, mid, mid + 1],
        [v_lo, mid, v_hi],
        [v_hi, v_lo, v_hi, v_lo],
    ]
    for xs in coverage_cases:
        clipped = [min(max(v, v_lo), v_hi) for v in xs]
        _append_query(queries, spec, clipped, QueryTag.COVERAGE)

    boundary_cases = [
        [],
        [v_lo],
        [v_hi],
        [mid],
    ]
    for xs in boundary_cases:
        _append_query(queries, spec, xs, QueryTag.BOUNDARY)

    for _ in range(4):
        sampled = _sample_sequence(
            length_range=axes.sequence_length_range,
            value_range=axes.value_range,
            rng=rng,
        )
        _append_query(queries, spec, sampled, QueryTag.TYPICAL)

    adversarial_cases = [
        [v_lo, v_hi] * 4,
        [mid] * 8,
        [v_hi] * 4 + [v_lo] * 4,
    ]
    for xs in adversarial_cases:
        _append_query(queries, spec, xs, QueryTag.ADVERSARIAL)

    for tag in QueryTag:
        if any(query.tag == tag for query in queries):
            continue
        _append_query(queries, spec, [mid], tag)

    deduped: list[Query] = []
    for tag in QueryTag:
        seen: set[tuple[int, ...]] = set()
        for query in queries:
            if query.tag != tag:
                continue
            frozen = tuple(int(v) for v in query.input)
            if frozen in seen:
                continue
            seen.add(frozen)
            deduped.append(query)

    return deduped
