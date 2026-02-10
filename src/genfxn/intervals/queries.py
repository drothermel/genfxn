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


def _clamp(value: int, lo: int, hi: int) -> int:
    return min(max(value, lo), hi)


def _sample_non_degenerate_interval(
    bounds: tuple[int, int],
    max_span_range: tuple[int, int],
    rng: random.Random,
) -> tuple[int, int] | None:
    lo, hi = bounds
    if lo >= hi:
        return None

    max_possible_span = hi - lo
    requested_lo = max(1, max_span_range[0])
    requested_hi = max_span_range[1]
    if requested_hi < requested_lo:
        return None
    span_hi = min(requested_hi, max_possible_span)
    if span_hi < requested_lo:
        return None

    span_lo = min(requested_lo, span_hi)
    span = rng.randint(span_lo, span_hi)
    start = rng.randint(lo, hi - span)
    return start, start + span


def _sample_interval(
    *,
    endpoint_range: tuple[int, int],
    max_span_range: tuple[int, int],
    existing_intervals: list[tuple[int, int]],
    allow_reversed_interval_prob: float,
    degenerate_interval_prob: float,
    nested_interval_prob: float,
    rng: random.Random,
) -> tuple[int, int]:
    lo, hi = endpoint_range
    bounds = endpoint_range

    if existing_intervals and rng.random() < nested_interval_prob:
        parent_a, parent_b = existing_intervals[
            rng.randrange(len(existing_intervals))
        ]
        bounds = (min(parent_a, parent_b), max(parent_a, parent_b))
        lo, hi = bounds

    must_be_degenerate = lo == hi or rng.random() < degenerate_interval_prob
    if must_be_degenerate:
        point = rng.randint(lo, hi)
        start = point
        end = point
    else:
        sampled = _sample_non_degenerate_interval(bounds, max_span_range, rng)
        if sampled is None:
            point = rng.randint(lo, hi)
            start = point
            end = point
        else:
            start, end = sampled

    if start != end and rng.random() < allow_reversed_interval_prob:
        start, end = end, start
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
    allow_reversed_interval_prob = spec.allow_reversed_interval_prob
    degenerate_interval_prob = spec.degenerate_interval_prob
    nested_interval_prob = spec.nested_interval_prob

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
            (_clamp(a, lo, hi), _clamp(b, lo, hi))
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
        adjusted = [
            (_clamp(a, lo, hi), _clamp(b, lo, hi))
            for a, b in case
        ]
        _append(adjusted, QueryTag.BOUNDARY)

    for _ in range(n_typical):
        count = rng.randint(max(0, n_lo), max(max(0, n_lo), n_hi))
        sampled: list[tuple[int, int]] = []
        for _ in range(count):
            sampled.append(
                _sample_interval(
                    endpoint_range=endpoint_range,
                    max_span_range=max_span_range,
                    existing_intervals=sampled,
                    allow_reversed_interval_prob=allow_reversed_interval_prob,
                    degenerate_interval_prob=degenerate_interval_prob,
                    nested_interval_prob=nested_interval_prob,
                    rng=rng,
                )
            )
        _append(sampled, QueryTag.TYPICAL)

    chain_size = max(2, min(6, max(n_lo, 2)))
    adversarial_cases = [
        _build_chain(lo, 1, chain_size),
        [(mid, mid), (mid, mid), (mid, mid + 1), (mid + 1, mid)],
        [(hi, lo), (lo, hi), (mid + 1, mid - 1)],
    ]
    for case in adversarial_cases:
        adjusted = [
            (_clamp(a, lo, hi), _clamp(b, lo, hi))
            for a, b in case
        ]
        _append(adjusted, QueryTag.ADVERSARIAL)

    for tag in QueryTag:
        if any(query.tag == tag for query in queries):
            continue
        tag_index = list(QueryTag).index(tag)
        fallback = [
            (
                _clamp(lo + tag_index, lo, hi),
                _clamp(hi - tag_index, lo, hi),
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
