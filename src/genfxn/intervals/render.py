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

    lines = [
        f"def {func_name}({var}: list[tuple[int, int]]) -> int:",
        f"    operation = {operation!r}",
        f"    boundary_mode = {boundary_mode!r}",
        f"    merge_touching = {merge_touching!r}",
        "",
        "    adjusted: list[tuple[int, int]] = []",
        f"    for raw_a, raw_b in {var}:",
        "        lo = min(raw_a, raw_b)",
        "        hi = max(raw_a, raw_b)",
        "",
        "        if boundary_mode == 'closed_closed':",
        "            start = lo",
        "            end = hi",
        "        elif boundary_mode == 'closed_open':",
        "            start = lo",
        "            end = hi - 1",
        "        elif boundary_mode == 'open_closed':",
        "            start = lo + 1",
        "            end = hi",
        "        elif boundary_mode == 'open_open':",
        "            start = lo + 1",
        "            end = hi - 1",
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
        "        threshold = prev_end + 1 if merge_touching else prev_end",
        "        if start <= threshold:",
        "            merged[-1] = (prev_start, max(prev_end, end))",
        "        else:",
        "            merged.append((start, end))",
        "",
        "    if operation == 'total_coverage':",
        "        total = 0",
        "        for start, end in merged:",
        "            total += (end - start + 1)",
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
        "            if next_start > prev_end + 1:",
        "                gaps += 1",
        "        return gaps",
        "",
        "    if operation == 'max_overlap_count':",
        "        events: dict[int, int] = {}",
        "        for start, end in adjusted:",
        "            events[start] = events.get(start, 0) + 1",
        "            next_point = end + 1",
        "            events[next_point] = events.get(next_point, 0) - 1",
        "",
        "        active = 0",
        "        best = 0",
        "        for point in sorted(events):",
        "            active += events[point]",
        "            if active > best:",
        "                best = active",
        "        return best",
        "",
        "    raise ValueError('Unsupported operation')",
    ]
    return "\n".join(lines)
