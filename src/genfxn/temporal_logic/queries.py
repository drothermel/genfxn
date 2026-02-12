import random

from genfxn.core.models import Query, QueryTag
from genfxn.temporal_logic.eval import eval_temporal_logic
from genfxn.temporal_logic.models import TemporalLogicAxes, TemporalLogicSpec
from genfxn.temporal_logic.utils import sample_sequence


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


def _fit_sequence_length(
    xs: list[int],
    length_range: tuple[int, int],
    *,
    fill_value: int,
) -> list[int]:
    lo, hi = length_range
    target_len = min(max(len(xs), lo), hi)
    if target_len <= 0:
        return []

    if not xs:
        xs = [fill_value]

    if len(xs) >= target_len:
        return xs[:target_len]

    fitted = list(xs)
    index = 0
    while len(fitted) < target_len:
        fitted.append(xs[index % len(xs)])
        index += 1
    return fitted


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
        clipped = _fit_sequence_length(
            clipped,
            axes.sequence_length_range,
            fill_value=mid,
        )
        _append_query(queries, spec, clipped, QueryTag.COVERAGE)

    boundary_cases = [
        [],
        [v_lo],
        [v_hi],
        [mid],
    ]
    for xs in boundary_cases:
        fitted = _fit_sequence_length(
            xs,
            axes.sequence_length_range,
            fill_value=mid,
        )
        _append_query(queries, spec, fitted, QueryTag.BOUNDARY)

    for _ in range(4):
        sampled = sample_sequence(
            length_range=axes.sequence_length_range,
            value_range=axes.value_range,
            rng=rng,
        )
        sampled = _fit_sequence_length(
            sampled,
            axes.sequence_length_range,
            fill_value=mid,
        )
        _append_query(queries, spec, sampled, QueryTag.TYPICAL)

    adversarial_cases = [
        [v_lo, v_hi] * 4,
        [mid] * 8,
        [v_hi] * 4 + [v_lo] * 4,
    ]
    for xs in adversarial_cases:
        fitted = _fit_sequence_length(
            xs,
            axes.sequence_length_range,
            fill_value=mid,
        )
        _append_query(queries, spec, fitted, QueryTag.ADVERSARIAL)

    for tag in QueryTag:
        if any(query.tag == tag for query in queries):
            continue
        fallback = _fit_sequence_length(
            [mid],
            axes.sequence_length_range,
            fill_value=mid,
        )
        _append_query(queries, spec, fallback, tag)

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
