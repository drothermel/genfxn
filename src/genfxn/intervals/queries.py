import random
from typing import Any

from genfxn.core.models import Query, QueryTag
from genfxn.intervals.eval import eval_intervals
from genfxn.intervals.models import IntervalsAxes, IntervalsSpec


def _ordered_pair(value: Any, fallback: tuple[int, int]) -> tuple[int, int]:
    if (
        isinstance(value, (tuple, list))
        and len(value) == 2
        and isinstance(value[0], int)
        and isinstance(value[1], int)
    ):
        lo = int(value[0])
        hi = int(value[1])
        if lo <= hi:
            return lo, hi
        return hi, lo
    return fallback


def _get_axis_range(
    axes: IntervalsAxes,
    candidates: tuple[str, ...],
    fallback: tuple[int, int],
) -> tuple[int, int]:
    for name in candidates:
        if hasattr(axes, name):
            return _ordered_pair(getattr(axes, name), fallback)
    return fallback


def _clamp(value: int, bounds: tuple[int, int]) -> int:
    lo, hi = bounds
    return min(max(value, lo), hi)


def _sample_interval(
    endpoint_range: tuple[int, int],
    max_span_range: tuple[int, int],
    rng: random.Random,
) -> tuple[int, int]:
    lo, hi = endpoint_range
    start = rng.randint(lo, hi)
    span_min = max(0, max_span_range[0])
    span_max = max(span_min, max_span_range[1])
    span = rng.randint(span_min, span_max)
    direction = -1 if rng.random() < 0.5 else 1
    end = _clamp(start + direction * span, endpoint_range)
    if rng.random() < 0.25:
        return end, start
    return start, end


def _build_chain(
    start: int,
    step: int,
    count: int,
) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    cursor = start
    for _ in range(max(0, count)):
        intervals.append((cursor, cursor + step))
        cursor += step + 1
    return intervals


def generate_intervals_queries(
    spec: IntervalsSpec,
    axes: IntervalsAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    endpoint_range = _get_axis_range(
        axes,
        ("endpoint_range", "value_range"),
        (-8, 8),
    )
    max_span_range = _get_axis_range(
        axes,
        ("max_span_range",),
        (0, endpoint_range[1] - endpoint_range[0]),
    )
    n_intervals_range = _get_axis_range(
        axes,
        ("n_intervals_range", "list_length_range", "input_length_range"),
        (1, 5),
    )
    n_lo, n_hi = n_intervals_range
    n_typical = max(1, min(4, n_hi if n_hi >= 1 else 1))
    lo, hi = endpoint_range
    mid = (lo + hi) // 2

    queries: list[Query] = []

    def _append(intervals: list[tuple[int, int]], tag: QueryTag) -> None:
        normalized = [(int(a), int(b)) for a, b in intervals]
        queries.append(
            Query(
                input=normalized,
                output=eval_intervals(spec, normalized),
                tag=tag,
            )
        )

    coverage_cases = [
        [],
        [(mid, mid)],
        [(lo, lo + 1), (lo + 1, lo + 2)],
        [(lo, lo + 3), (lo + 2, lo + 5)],
    ]
    for case in coverage_cases:
        adjusted = [
            (_clamp(a, endpoint_range), _clamp(b, endpoint_range))
            for a, b in case
        ]
        _append(adjusted, QueryTag.COVERAGE)

    boundary_cases = [
        [(lo, hi)],
        [(hi, lo)],
        [(lo, lo)],
        [(hi, hi)],
        [(lo, lo + 1)],
    ]
    for case in boundary_cases:
        _append(case, QueryTag.BOUNDARY)

    for _ in range(n_typical):
        count = rng.randint(max(0, n_lo), max(max(0, n_lo), n_hi))
        sampled = [
            _sample_interval(endpoint_range, max_span_range, rng)
            for _ in range(count)
        ]
        _append(sampled, QueryTag.TYPICAL)

    chain_size = max(2, min(6, max(n_lo, 2)))
    adversarial_cases = [
        _build_chain(lo, 1, chain_size),
        [(mid, mid), (mid, mid), (mid, mid + 1), (mid + 1, mid)],
        [(hi, lo), (lo, hi), (mid + 1, mid - 1)],
    ]
    for case in adversarial_cases:
        adjusted = [
            (_clamp(a, endpoint_range), _clamp(b, endpoint_range))
            for a, b in case
        ]
        _append(adjusted, QueryTag.ADVERSARIAL)

    for tag in QueryTag:
        if any(query.tag == tag for query in queries):
            continue
        tag_index = list(QueryTag).index(tag)
        fallback = [
            (
                _clamp(lo + tag_index, endpoint_range),
                _clamp(hi - tag_index, endpoint_range),
            )
        ]
        _append(fallback, tag)

    deduped: list[Query] = []
    for tag in QueryTag:
        seen: set[tuple[tuple[int, int], ...]] = set()
        for query in queries:
            if query.tag != tag:
                continue
            frozen = tuple((int(a), int(b)) for a, b in query.input)
            if frozen in seen:
                continue
            seen.add(frozen)
            deduped.append(query)

    return deduped
