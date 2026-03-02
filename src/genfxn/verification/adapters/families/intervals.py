from __future__ import annotations

from typing import Any, cast

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.intervals.eval import eval_intervals
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    DEFAULT_INT_RANGE,
    collect_int_constants,
    deterministic_rng,
    nonnegative_range,
    range_from_axes,
)
from genfxn.verification.adapters.families._shared import (
    choose_extra_int_edges,
    int_strategy,
    to_spec_dict,
)
from genfxn.verification.adapters.mutations import (
    candidate,
    finalize_candidates,
    i64_add,
    set_at_path,
)

FAMILY = "intervals"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("intervals input must be list[tuple[int,int]]")
    return eval_intervals(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    endpoint_range = range_from_axes(axes, "endpoint_range", DEFAULT_INT_RANGE)
    list_length_range = nonnegative_range(
        range_from_axes(axes, "n_intervals_range", (0, 10))
    )
    lo, hi = endpoint_range
    constants = collect_int_constants(to_spec_dict(spec_obj))

    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    int_values = [lo, hi, 0, 1, -1]
    for constant in constants[:10]:
        int_values.extend([constant - 1, constant, constant + 1])
    int_values.extend(
        choose_extra_int_edges(
            lo=lo,
            hi=hi,
            constants=constants,
            rng=rng,
            count=40,
        )
    )
    point_strategy = int_strategy(lo=lo, hi=hi, edge_values=int_values)
    pair_strategy = st.tuples(point_strategy, point_strategy)
    generated = st.lists(
        pair_strategy,
        min_size=list_length_range[0],
        max_size=list_length_range[1],
    )

    edge_cases: list[list[tuple[int, int]]] = [
        [],
        [(0, 0)],
        [(0, 1)],
        [(1, 0)],
        [(lo, hi)],
        [(hi, lo)],
    ]
    if constants:
        c = constants[0]
        edge_cases.append([(c - 1, c), (c, c + 1)])

    return st.one_of(st.sampled_from(edge_cases), generated)


def _layer3_mutants(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    spec_dict: dict[str, Any],
    budget: int,
    seed: int,
    mode: str,
) -> list[Any]:
    candidates: list[Any] = []

    operation = spec_dict.get("operation")
    operation_alternate = {
        "total_coverage": "merged_count",
        "merged_count": "max_overlap_count",
        "max_overlap_count": "gap_count",
        "gap_count": "total_coverage",
    }.get(operation)
    if operation_alternate is not None:
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("operation",), operation_alternate),
                mutant_kind="intervals_operation_mutation",
                rule_id="intervals.operation_swap",
                metadata={"path": ["operation"], "to": operation_alternate},
            )
        )

    boundary_mode = spec_dict.get("boundary_mode")
    boundary_alternate = {
        "closed_closed": "closed_open",
        "closed_open": "open_closed",
        "open_closed": "open_open",
        "open_open": "closed_closed",
    }.get(boundary_mode)
    if boundary_alternate is not None:
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("boundary_mode",), boundary_alternate),
                mutant_kind="intervals_boundary_mutation",
                rule_id="intervals.boundary_mode_swap",
                metadata={"path": ["boundary_mode"], "to": boundary_alternate},
            )
        )

    merge_touching = spec_dict.get("merge_touching")
    if isinstance(merge_touching, bool):
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("merge_touching",), not merge_touching),
                mutant_kind="intervals_merge_mutation",
                rule_id="intervals.merge_touching_flip",
                metadata={"path": ["merge_touching"]},
            )
        )

    for field_name in ("endpoint_clip_abs", "endpoint_quantize_step"):
        value = spec_dict.get(field_name)
        if type(value) is not int:
            continue
        for delta in (-1, 1):
            updated = i64_add(value, delta)
            if updated is None or updated < 1:
                continue
            candidates.append(
                candidate(
                    set_at_path(spec_dict, (field_name,), updated),
                    mutant_kind="intervals_numeric_mutation",
                    rule_id=(
                        f"intervals.{field_name}_"
                        f"{'minus' if delta < 0 else 'plus'}_one"
                    ),
                    metadata={"path": [field_name], "delta": delta},
                )
            )

    return finalize_candidates(
        candidates,
        validate_spec=lambda raw: validate_spec_for_family(FAMILY, raw),
        original_spec=spec_dict,
        task_id=task_id,
        family=FAMILY,
        seed=seed,
        mode=cast(Any, mode),
        budget=budget,
    )


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
    layer3_mutant_factory=_layer3_mutants,
)
