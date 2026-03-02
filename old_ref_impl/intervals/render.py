from typing import Any

from genfxn.intervals.models import IntervalsSpec


def _get_str_field(
    spec_dict: dict[str, Any],
    candidates: tuple[str, ...],
    default: str,
) -> str:
    for name in candidates:
        value = spec_dict.get(name)
        if value is None:
            continue
        member_value = getattr(value, "value", value)
        if isinstance(member_value, str):
            return member_value
    return default


def _get_bool_field(
    spec_dict: dict[str, Any],
    candidates: tuple[str, ...],
    default: bool,
) -> bool:
    for name in candidates:
        value = spec_dict.get(name)
        if isinstance(value, bool):
            return value
    return default


def _get_int_field(
    spec_dict: dict[str, Any],
    candidates: tuple[str, ...],
    default: int,
) -> int:
    for name in candidates:
        value = spec_dict.get(name)
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return default


def render_intervals(
    spec: IntervalsSpec,
    func_name: str = "f",
    var: str = "intervals",
) -> str:
    spec_dict = spec.model_dump()
    operation = _get_str_field(
        spec_dict,
        ("operation", "operation_type", "output"),
        "total_coverage",
    )
    boundary_mode = _get_str_field(
        spec_dict,
        ("boundary_mode", "boundary"),
        "closed_closed",
    )
    merge_touching = _get_bool_field(
        spec_dict,
        ("merge_touching",),
        True,
    )
    endpoint_clip_abs = _get_int_field(
        spec_dict,
        ("endpoint_clip_abs",),
        20,
    )
    endpoint_quantize_step = _get_int_field(
        spec_dict,
        ("endpoint_quantize_step",),
        1,
    )

    lines = [
        f"def {func_name}({var}: list[tuple[int, int]]) -> int:",
        f"    operation = {operation!r}",
        f"    boundary_mode = {boundary_mode!r}",
        f"    merge_touching = {merge_touching!r}",
        f"    endpoint_clip_abs = {endpoint_clip_abs}",
        f"    endpoint_quantize_step = {endpoint_quantize_step}",
        "    _i64_mask = (1 << 64) - 1",
        "",
        "    def _wrap_i64(value: int) -> int:",
        "        wrapped = value & _i64_mask",
        "        if wrapped >= (1 << 63):",
        "            return wrapped - (1 << 64)",
        "        return wrapped",
        "",
        "    def _quantize(v: int) -> int:",
        "        if endpoint_quantize_step <= 1:",
        "            return v",
        "        magnitude = abs(v) // endpoint_quantize_step",
        "        q = magnitude * endpoint_quantize_step",
        "        return q if v >= 0 else -q",
        "",
        "    adjusted: list[tuple[int, int]] = []",
        f"    for raw_a, raw_b in {var}:",
        "        raw_a = min(endpoint_clip_abs, raw_a)",
        "        raw_a = max(-endpoint_clip_abs, raw_a)",
        "        raw_b = min(endpoint_clip_abs, raw_b)",
        "        raw_b = max(-endpoint_clip_abs, raw_b)",
        "        raw_a = _quantize(raw_a)",
        "        raw_b = _quantize(raw_b)",
        "        lo = min(raw_a, raw_b)",
        "        hi = max(raw_a, raw_b)",
        "",
        "        if boundary_mode == 'closed_closed':",
        "            start = lo",
        "            end = hi",
        "        elif boundary_mode == 'closed_open':",
        "            start = lo",
        "            end = _wrap_i64(hi - 1)",
        "        elif boundary_mode == 'open_closed':",
        "            start = _wrap_i64(lo + 1)",
        "            end = hi",
        "        elif boundary_mode == 'open_open':",
        "            start = _wrap_i64(lo + 1)",
        "            end = _wrap_i64(hi - 1)",
        "        else:",
        "            raise ValueError('Unsupported boundary mode')",
        "",
        "        if start <= end:",
        "            adjusted.append((start, end))",
        "",
        "    if not adjusted:",
        "        return 0",
        "",
        "    adjusted.sort()",
        "    merged: list[tuple[int, int]] = [adjusted[0]]",
        "    for start, end in adjusted[1:]:",
        "        prev_start, prev_end = merged[-1]",
        "        threshold = (",
        "            _wrap_i64(prev_end + 1) if merge_touching else prev_end",
        "        )",
        "        if start <= threshold:",
        "            merged[-1] = (prev_start, max(prev_end, end))",
        "        else:",
        "            merged.append((start, end))",
        "",
        "    if operation == 'total_coverage':",
        "        total = 0",
        "        for start, end in merged:",
        "            span_size = _wrap_i64(_wrap_i64(end - start) + 1)",
        "            total = _wrap_i64(total + span_size)",
        "        return total",
        "",
        "    if operation == 'merged_count':",
        "        return len(merged)",
        "",
        "    if operation == 'gap_count':",
        "        gaps = 0",
        "        for idx in range(1, len(merged)):",
        "            prev_end = merged[idx - 1][1]",
        "            next_start = merged[idx][0]",
        "            if next_start > _wrap_i64(prev_end + 1):",
        "                gaps = _wrap_i64(gaps + 1)",
        "        return gaps",
        "",
        "    if operation == 'max_overlap_count':",
        "        events: dict[int, int] = {}",
        "        for start, end in adjusted:",
        "            events[start] = _wrap_i64(events.get(start, 0) + 1)",
        "            next_point = _wrap_i64(end + 1)",
        "            events[next_point] = _wrap_i64(",
        "                events.get(next_point, 0) - 1",
        "            )",
        "",
        "        active = 0",
        "        best = 0",
        "        for point in sorted(events):",
        "            active = _wrap_i64(active + events[point])",
        "            if active > best:",
        "                best = active",
        "        return best",
        "",
        "    raise ValueError('Unsupported operation')",
    ]
    return "\n".join(lines)
