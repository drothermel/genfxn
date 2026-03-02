from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from genfxn.core.models import Task
from genfxn.verification.adapters import evaluate_input, validate_spec_for_task
from genfxn.verification.models import (
    VerificationCase,
    VerificationLayer,
    normalize_case_value,
)

_DEFAULT_INT_RANGE = (-100, 100)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Layer1Candidate:
    input_value: Any
    source_detail: dict[str, Any]


def _freeze_case_value(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return ("scalar", "nan")
    if type(value) in {int, float, str, bool, type(None)}:
        return ("scalar", type(value).__name__, value)
    if isinstance(value, list):
        return ("list", tuple(_freeze_case_value(item) for item in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(_freeze_case_value(item) for item in value))
    if isinstance(value, dict):
        frozen_items = [
            (_freeze_case_value(key), _freeze_case_value(val))
            for key, val in value.items()
        ]
        return (
            "dict",
            tuple(
                sorted(
                    frozen_items,
                    key=lambda item: (
                        repr(item[0]),
                        repr(item[1]),
                    ),
                )
            ),
        )
    return ("repr", type(value).__name__, repr(value))


def _dedupe_candidates(
    candidates: list[_Layer1Candidate],
) -> list[_Layer1Candidate]:
    seen: set[Any] = set()
    result: list[_Layer1Candidate] = []
    for candidate in candidates:
        key = _freeze_case_value(candidate.input_value)
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _range_from_axes(
    axes: dict[str, Any] | None,
    key: str,
    default: tuple[int, int],
) -> tuple[int, int]:
    if axes is None:
        return default
    value = axes.get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default
    lo, hi = value
    if isinstance(lo, bool) or isinstance(hi, bool):
        return default
    if not isinstance(lo, int) or not isinstance(hi, int):
        return default
    if lo > hi:
        return default
    return lo, hi


def _collect_int_constants(value: Any) -> list[int]:
    constants: set[int] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int):
            constants.add(node)
            return
        if isinstance(node, list | tuple | set | frozenset):
            for child in node:
                _visit(child)
            return
        if isinstance(node, dict):
            for child in node.values():
                _visit(child)

    _visit(value)
    return sorted(constants)


def _collect_thresholds(value: Any) -> list[int]:
    thresholds: set[int] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, dict):
            kind = node.get("kind")
            raw_value = node.get("value")
            if kind in {"lt", "le", "gt", "ge"} and isinstance(raw_value, int):
                thresholds.add(raw_value)
            for child in node.values():
                _visit(child)
            return
        if isinstance(node, list | tuple):
            for child in node:
                _visit(child)

    _visit(value)
    return sorted(thresholds)


def _collect_string_fragments(value: Any) -> list[str]:
    fragments: list[str] = []

    def _visit(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("prefix", "suffix", "substring"):
                raw = node.get(key)
                if isinstance(raw, str) and raw:
                    fragments.append(raw)
            for child in node.values():
                _visit(child)
            return
        if isinstance(node, list | tuple):
            for child in node:
                _visit(child)

    _visit(value)
    return sorted(
        set(fragments), key=lambda fragment: (len(fragment), fragment)
    )


def _collect_string_length_thresholds(value: Any) -> list[int]:
    thresholds: set[int] = set()

    def _visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("kind") == "length_cmp":
                raw_value = node.get("value")
                if isinstance(raw_value, int) and raw_value >= 0:
                    thresholds.add(raw_value)
            for child in node.values():
                _visit(child)
            return
        if isinstance(node, list | tuple):
            for child in node:
                _visit(child)

    _visit(value)
    return sorted(thresholds)


def _scalar_int_candidates(
    *,
    axes: dict[str, Any] | None,
    constants: list[int],
) -> list[_Layer1Candidate]:
    lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
    candidates = [
        _Layer1Candidate(lo, {"boundary_type": "value_range_low"}),
        _Layer1Candidate(lo + 1, {"boundary_type": "value_range_low_plus_one"}),
        _Layer1Candidate(
            hi - 1, {"boundary_type": "value_range_high_minus_one"}
        ),
        _Layer1Candidate(hi, {"boundary_type": "value_range_high"}),
        _Layer1Candidate(0, {"boundary_type": "zero"}),
        _Layer1Candidate(-1, {"boundary_type": "minus_one"}),
        _Layer1Candidate(1, {"boundary_type": "plus_one"}),
    ]
    for constant in constants[:8]:
        candidates.extend(
            (
                _Layer1Candidate(
                    constant - 1,
                    {
                        "boundary_type": "spec_constant_neighbor",
                        "constant": constant,
                    },
                ),
                _Layer1Candidate(
                    constant,
                    {"boundary_type": "spec_constant", "constant": constant},
                ),
                _Layer1Candidate(
                    constant + 1,
                    {
                        "boundary_type": "spec_constant_neighbor",
                        "constant": constant,
                    },
                ),
            )
        )
    return candidates


def _list_int_candidates(
    *,
    axes: dict[str, Any] | None,
    constants: list[int],
    length_key: str = "list_length_range",
) -> list[_Layer1Candidate]:
    lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
    len_lo, len_hi = _range_from_axes(axes, length_key, (0, 12))
    len_hi = min(len_hi, 12)
    if len_lo > len_hi:
        len_lo = len_hi

    candidates: list[_Layer1Candidate] = [
        _Layer1Candidate([], {"boundary_type": "size_empty"}),
        _Layer1Candidate([lo], {"boundary_type": "size_one_value_low"}),
        _Layer1Candidate([hi], {"boundary_type": "size_one_value_high"}),
        _Layer1Candidate([0], {"boundary_type": "size_one_zero"}),
        _Layer1Candidate([1, -1], {"boundary_type": "sign_flip_pair"}),
        _Layer1Candidate([lo, hi], {"boundary_type": "value_range_pair"}),
    ]

    size_points = {len_lo, min(len_lo + 1, len_hi), len_hi}
    for size in sorted(size_points):
        if size <= 0:
            continue
        candidates.append(
            _Layer1Candidate(
                [0] * size,
                {"boundary_type": "size_boundary", "size": size},
            )
        )
        alternating = [lo if index % 2 == 0 else hi for index in range(size)]
        candidates.append(
            _Layer1Candidate(
                alternating,
                {
                    "boundary_type": "size_boundary_alternating",
                    "size": size,
                },
            )
        )

    for constant in constants[:4]:
        candidates.extend(
            (
                _Layer1Candidate(
                    [constant],
                    {"boundary_type": "spec_constant_singleton"},
                ),
                _Layer1Candidate(
                    [constant - 1, constant, constant + 1],
                    {"boundary_type": "spec_constant_triplet"},
                ),
            )
        )

    return candidates


def _sequence_dp_candidates(
    *,
    axes: dict[str, Any] | None,
    constants: list[int],
) -> list[_Layer1Candidate]:
    lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
    len_a_lo, len_a_hi = _range_from_axes(axes, "len_a_range", (0, 8))
    len_b_lo, len_b_hi = _range_from_axes(axes, "len_b_range", (0, 8))
    len_a_hi = min(len_a_hi, 10)
    len_b_hi = min(len_b_hi, 10)
    if len_a_lo > len_a_hi:
        len_a_lo = len_a_hi
    if len_b_lo > len_b_hi:
        len_b_lo = len_b_hi

    candidates: list[_Layer1Candidate] = [
        _Layer1Candidate(
            {"a": [], "b": []},
            {"boundary_type": "both_empty"},
        ),
        _Layer1Candidate(
            {"a": [0], "b": [0]},
            {"boundary_type": "singleton_equal"},
        ),
        _Layer1Candidate(
            {"a": [lo], "b": [hi]},
            {"boundary_type": "value_range_extremes"},
        ),
        _Layer1Candidate(
            {"a": [1, -1], "b": [-1, 1]},
            {"boundary_type": "sign_flip_pair"},
        ),
    ]

    for size in sorted({len_a_lo, min(len_a_lo + 1, len_a_hi), len_a_hi}):
        if size <= 0:
            continue
        candidates.append(
            _Layer1Candidate(
                {"a": [0] * size, "b": []},
                {"boundary_type": "len_a_boundary", "size": size},
            )
        )
    for size in sorted({len_b_lo, min(len_b_lo + 1, len_b_hi), len_b_hi}):
        if size <= 0:
            continue
        candidates.append(
            _Layer1Candidate(
                {"a": [], "b": [0] * size},
                {"boundary_type": "len_b_boundary", "size": size},
            )
        )

    for constant in constants[:3]:
        candidates.append(
            _Layer1Candidate(
                {"a": [constant], "b": [constant]},
                {"boundary_type": "spec_constant_match"},
            )
        )
        candidates.append(
            _Layer1Candidate(
                {"a": [constant - 1, constant], "b": [constant, constant + 1]},
                {"boundary_type": "spec_constant_neighbors"},
            )
        )

    return candidates


def _interval_candidates(
    *,
    constants: list[int],
    endpoint_clip_abs: int,
) -> list[_Layer1Candidate]:
    clip = max(1, min(endpoint_clip_abs, 24))
    candidates: list[_Layer1Candidate] = [
        _Layer1Candidate([], {"boundary_type": "empty"}),
        _Layer1Candidate([(0, 0)], {"boundary_type": "degenerate_interval"}),
        _Layer1Candidate([(0, 1)], {"boundary_type": "size_one_span"}),
        _Layer1Candidate([(1, 0)], {"boundary_type": "reversed_interval"}),
        _Layer1Candidate(
            [(-clip, clip)],
            {"boundary_type": "clip_boundary"},
        ),
        _Layer1Candidate(
            [(0, 1), (1, 2)],
            {"boundary_type": "touching_intervals"},
        ),
        _Layer1Candidate(
            [(-2, 2), (-1, 1)],
            {"boundary_type": "nested_intervals"},
        ),
    ]
    for constant in constants[:3]:
        candidates.append(
            _Layer1Candidate(
                [(constant - 1, constant), (constant, constant + 1)],
                {"boundary_type": "spec_constant_intervals"},
            )
        )
    return candidates


def _graph_query_candidates(spec_obj: Any) -> list[_Layer1Candidate]:
    n_nodes = int(getattr(spec_obj, "n_nodes", 1))
    last = max(0, n_nodes - 1)
    mid = last // 2
    candidates: list[_Layer1Candidate] = [
        _Layer1Candidate(
            {"src": 0, "dst": 0}, {"boundary_type": "node_origin"}
        ),
        _Layer1Candidate(
            {"src": 0, "dst": last},
            {"boundary_type": "node_first_to_last"},
        ),
        _Layer1Candidate(
            {"src": last, "dst": 0},
            {"boundary_type": "node_last_to_first"},
        ),
        _Layer1Candidate(
            {"src": last, "dst": last},
            {"boundary_type": "node_last_self"},
        ),
        _Layer1Candidate(
            {"src": mid, "dst": mid},
            {"boundary_type": "node_mid_self"},
        ),
    ]
    for edge in getattr(spec_obj, "edges", [])[:4]:
        candidates.extend(
            (
                _Layer1Candidate(
                    {"src": int(edge.u), "dst": int(edge.v)},
                    {"boundary_type": "edge_endpoint"},
                ),
                _Layer1Candidate(
                    {"src": int(edge.v), "dst": int(edge.u)},
                    {"boundary_type": "edge_reverse_endpoint"},
                ),
            )
        )
    return candidates


def _string_candidates(task: Task) -> list[_Layer1Candidate]:
    string_fragments = _collect_string_fragments(task.spec)
    length_thresholds = _collect_string_length_thresholds(task.spec)
    len_lo, len_hi = _range_from_axes(task.axes, "string_length_range", (0, 20))
    len_hi = min(len_hi, 24)
    if len_lo > len_hi:
        len_lo = len_hi

    candidates: list[_Layer1Candidate] = [
        _Layer1Candidate("", {"boundary_type": "empty"}),
        _Layer1Candidate("a", {"boundary_type": "single_lower"}),
        _Layer1Candidate("A", {"boundary_type": "single_upper"}),
        _Layer1Candidate("0", {"boundary_type": "single_digit"}),
        _Layer1Candidate("aa", {"boundary_type": "double_lower"}),
        _Layer1Candidate("AA", {"boundary_type": "double_upper"}),
        _Layer1Candidate("a0", {"boundary_type": "alnum"}),
        _Layer1Candidate("  ", {"boundary_type": "spaces"}),
    ]
    for size in sorted({len_lo, min(len_lo + 1, len_hi), len_hi}):
        candidates.append(
            _Layer1Candidate(
                "a" * max(0, size),
                {"boundary_type": "length_boundary", "size": size},
            )
        )
    for threshold in length_thresholds[:5]:
        for delta in (-1, 0, 1):
            target_len = max(0, threshold + delta)
            candidates.append(
                _Layer1Candidate(
                    "a" * target_len,
                    {
                        "boundary_type": "predicate_length_threshold",
                        "threshold": threshold,
                        "delta": delta,
                    },
                )
            )
    for fragment in string_fragments[:8]:
        candidates.extend(
            (
                _Layer1Candidate(
                    fragment,
                    {
                        "boundary_type": "predicate_fragment_exact",
                        "fragment": fragment,
                    },
                ),
                _Layer1Candidate(
                    f"x{fragment}",
                    {
                        "boundary_type": "predicate_fragment_prefix_noise",
                        "fragment": fragment,
                    },
                ),
                _Layer1Candidate(
                    f"{fragment}x",
                    {
                        "boundary_type": "predicate_fragment_suffix_noise",
                        "fragment": fragment,
                    },
                ),
            )
        )
    return candidates


def _piecewise_candidates(task: Task) -> list[_Layer1Candidate]:
    constants = _collect_int_constants(task.spec)
    thresholds = _collect_thresholds(task.spec)
    candidates = _scalar_int_candidates(axes=task.axes, constants=constants)
    for threshold in thresholds[:12]:
        for delta in (-1, 0, 1):
            candidates.append(
                _Layer1Candidate(
                    threshold + delta,
                    {
                        "boundary_type": "branch_threshold",
                        "threshold": threshold,
                        "delta": delta,
                    },
                )
            )
    return candidates


def _bitops_candidates(task: Task, spec_obj: Any) -> list[_Layer1Candidate]:
    constants = _collect_int_constants(task.spec)
    candidates = _scalar_int_candidates(axes=task.axes, constants=constants)
    width_bits = int(getattr(spec_obj, "width_bits", 8))
    mask = (1 << width_bits) - 1
    candidates.extend(
        (
            _Layer1Candidate(0, {"boundary_type": "mask_zero"}),
            _Layer1Candidate(1, {"boundary_type": "mask_one"}),
            _Layer1Candidate(mask - 1, {"boundary_type": "mask_minus_one"}),
            _Layer1Candidate(mask, {"boundary_type": "mask_exact"}),
            _Layer1Candidate(mask + 1, {"boundary_type": "mask_plus_one"}),
            _Layer1Candidate(-mask, {"boundary_type": "negative_mask"}),
        )
    )
    return candidates


def _layer1_candidates_for_task(
    task: Task, spec_obj: Any
) -> list[_Layer1Candidate]:
    constants = _collect_int_constants(task.spec)

    if task.family == "piecewise":
        return _piecewise_candidates(task)
    if task.family == "bitops":
        return _bitops_candidates(task, spec_obj)
    if task.family == "stringrules":
        return _string_candidates(task)
    if task.family == "sequence_dp":
        return _sequence_dp_candidates(axes=task.axes, constants=constants)
    if task.family == "intervals":
        endpoint_clip_abs = int(getattr(spec_obj, "endpoint_clip_abs", 20))
        return _interval_candidates(
            constants=constants,
            endpoint_clip_abs=endpoint_clip_abs,
        )
    if task.family == "graph_queries":
        return _graph_query_candidates(spec_obj)
    if task.family in {
        "stateful",
        "simple_algorithms",
        "stack_bytecode",
        "fsm",
    }:
        return _list_int_candidates(axes=task.axes, constants=constants)
    if task.family == "temporal_logic":
        return _list_int_candidates(
            axes=task.axes,
            constants=constants,
            length_key="sequence_length_range",
        )
    raise ValueError(f"Unsupported family for layer1 generation: {task.family}")


def generate_layer1_cases(task: Task) -> list[VerificationCase]:
    spec_obj = validate_spec_for_task(task.family, task.spec)
    candidates = _dedupe_candidates(_layer1_candidates_for_task(task, spec_obj))

    cases: list[VerificationCase] = []
    for candidate in candidates:
        try:
            expected = normalize_case_value(
                evaluate_input(task.family, spec_obj, candidate.input_value)
            )
        except Exception as exc:
            logger.debug(
                "Skipping layer1 candidate evaluation for task %s input=%r: %s",
                task.task_id,
                candidate.input_value,
                exc,
                exc_info=True,
            )
            continue

        idx = len(cases)
        cases.append(
            VerificationCase(
                task_id=task.task_id,
                family=task.family,
                layer=VerificationLayer.LAYER1_SPEC_BOUNDARY,
                case_id=f"layer1-{idx:04d}",
                input=candidate.input_value,
                expected_output=expected,
                source_detail=candidate.source_detail,
            )
        )
    return cases
