from genfxn.intervals.models import BoundaryMode, IntervalsSpec, OperationType

Span = tuple[int, int]


def _clip_endpoint(value: int, endpoint_clip_abs: int) -> int:
    return min(max(value, -endpoint_clip_abs), endpoint_clip_abs)


def _quantize_endpoint(value: int, endpoint_quantize_step: int) -> int:
    if endpoint_quantize_step <= 1:
        return value
    magnitude = abs(value) // endpoint_quantize_step
    quantized = magnitude * endpoint_quantize_step
    return quantized if value >= 0 else -quantized


def _adjust_span(
    a: int,
    b: int,
    boundary_mode: BoundaryMode,
    endpoint_clip_abs: int,
    endpoint_quantize_step: int,
) -> Span | None:
    a = _clip_endpoint(a, endpoint_clip_abs)
    b = _clip_endpoint(b, endpoint_clip_abs)
    a = _quantize_endpoint(a, endpoint_quantize_step)
    b = _quantize_endpoint(b, endpoint_quantize_step)
    lo = min(a, b)
    hi = max(a, b)

    if boundary_mode == BoundaryMode.CLOSED_CLOSED:
        start, end = lo, hi
    elif boundary_mode == BoundaryMode.CLOSED_OPEN:
        start, end = lo, hi - 1
    elif boundary_mode == BoundaryMode.OPEN_CLOSED:
        start, end = lo + 1, hi
    else:
        start, end = lo + 1, hi - 1

    if start > end:
        return None
    return (start, end)


def _effective_spans(
    boundary_mode: BoundaryMode,
    endpoint_clip_abs: int,
    endpoint_quantize_step: int,
    intervals: list[tuple[int, int]],
) -> list[Span]:
    spans: list[Span] = []
    for a, b in intervals:
        span = _adjust_span(
            a,
            b,
            boundary_mode,
            endpoint_clip_abs,
            endpoint_quantize_step,
        )
        if span is not None:
            spans.append(span)
    return spans


def _merge_spans(spans: list[Span], merge_touching: bool) -> list[Span]:
    if not spans:
        return []

    sorted_spans = sorted(spans, key=lambda span: (span[0], span[1]))
    merged: list[Span] = [sorted_spans[0]]

    for start, end in sorted_spans[1:]:
        cur_start, cur_end = merged[-1]
        merge_threshold = cur_end + 1 if merge_touching else cur_end

        if start <= merge_threshold:
            merged[-1] = (cur_start, max(cur_end, end))
            continue

        merged.append((start, end))

    return merged


def _total_coverage(merged_spans: list[Span]) -> int:
    return sum(end - start + 1 for start, end in merged_spans)


def _max_overlap_count(spans: list[Span]) -> int:
    events: dict[int, int] = {}
    for start, end in spans:
        events[start] = events.get(start, 0) + 1
        events[end + 1] = events.get(end + 1, 0) - 1

    active = 0
    max_active = 0
    for point in sorted(events):
        active += events[point]
        max_active = max(max_active, active)
    return max_active


def _gap_count(merged_spans: list[Span]) -> int:
    if len(merged_spans) < 2:
        return 0

    count = 0
    prev_end = merged_spans[0][1]
    for start, end in merged_spans[1:]:
        if start > prev_end + 1:
            count += 1
        prev_end = end
    return count


def eval_intervals(
    spec: IntervalsSpec,
    intervals: list[tuple[int, int]],
) -> int:
    spans = _effective_spans(
        spec.boundary_mode,
        spec.endpoint_clip_abs,
        spec.endpoint_quantize_step,
        intervals,
    )
    if not spans:
        return 0

    merged_spans = _merge_spans(spans, merge_touching=spec.merge_touching)

    if spec.operation == OperationType.TOTAL_COVERAGE:
        return _total_coverage(merged_spans)
    if spec.operation == OperationType.MERGED_COUNT:
        return len(merged_spans)
    if spec.operation == OperationType.MAX_OVERLAP_COUNT:
        return _max_overlap_count(spans)
    return _gap_count(merged_spans)
