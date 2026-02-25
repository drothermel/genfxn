from __future__ import annotations

from typing import Any, cast

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.temporal_logic.eval import eval_temporal_logic
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    DEFAULT_INT_RANGE,
    DEFAULT_LIST_LENGTH_RANGE,
    collect_int_constants,
    deterministic_rng,
    nonnegative_range,
    range_from_axes,
)
from genfxn.verification.adapters.families._shared import (
    choose_extra_int_edges,
    int_list_strategy,
    int_strategy,
    to_spec_dict,
)
from genfxn.verification.adapters.mutations import (
    candidate,
    finalize_candidates,
    i64_add,
    set_at_path,
    walk_nodes,
)

FAMILY = "temporal_logic"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("temporal_logic input must be list[int]")
    return eval_temporal_logic(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    value_range = range_from_axes(axes, "value_range", DEFAULT_INT_RANGE)
    length_key = (
        "sequence_length_range"
        if axes is not None and "sequence_length_range" in axes
        else "list_length_range"
    )
    length_range = nonnegative_range(
        range_from_axes(
            axes,
            length_key,
            DEFAULT_LIST_LENGTH_RANGE,
        )
    )
    lo, hi = value_range
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
            count=48,
        )
    )

    int_value_strategy = int_strategy(lo=lo, hi=hi, edge_values=int_values)
    edge_lists = [[], [lo], [hi], [0], [1, -1], [lo, hi]]
    for c in constants[:10]:
        edge_lists.extend([[c], [c - 1, c, c + 1]])
    edge_lists = [
        values
        for values in edge_lists
        if length_range[0] <= len(values) <= length_range[1]
    ]

    return int_list_strategy(
        int_value_strategy=int_value_strategy,
        length_range=length_range,
        edge_lists=edge_lists,
    )


def _layer3_mutants(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    spec_dict: dict[str, Any],
    budget: int,
    seed: int,
    mode: str,
) -> list[Any]:
    candidates: list[Any] = []

    output_mode = spec_dict.get("output_mode")
    output_alt = {
        "sat_at_start": "sat_count",
        "sat_count": "first_sat_index",
        "first_sat_index": "sat_at_start",
    }.get(output_mode)
    if output_alt is not None:
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("output_mode",), output_alt),
                mutant_kind="temporal_logic_output_mode_mutation",
                rule_id="temporal_logic.output_mode_swap",
                metadata={"path": ["output_mode"], "to": output_alt},
            )
        )

    op_swaps = {
        "and": "or",
        "or": "and",
        "eventually": "always",
        "always": "eventually",
        "until": "since",
        "since": "until",
    }
    pred_swaps = {
        "eq": "ne",
        "ne": "eq",
        "lt": "le",
        "le": "lt",
        "gt": "ge",
        "ge": "gt",
    }
    unary_ops = {"not", "next", "eventually", "always"}
    binary_ops = {"and", "or", "until", "since"}

    for path, node in walk_nodes(spec_dict.get("formula")):
        if not isinstance(node, dict):
            continue
        if "op" not in node:
            continue
        full_path = ("formula", *path)
        op = node.get("op")
        swap = op_swaps.get(op)
        if swap is not None:
            mutated_node = dict(node)
            mutated_node["op"] = swap
            candidates.append(
                candidate(
                    set_at_path(spec_dict, full_path, mutated_node),
                    mutant_kind="temporal_logic_operator_mutation",
                    rule_id="temporal_logic.swap_operator",
                    metadata={"path": list(full_path), "from": op, "to": swap},
                )
            )

        if op == "atom":
            predicate = node.get("predicate")
            pred_swap = pred_swaps.get(predicate)
            if pred_swap is not None:
                mutated_node = dict(node)
                mutated_node["predicate"] = pred_swap
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, full_path, mutated_node),
                        mutant_kind="temporal_logic_predicate_mutation",
                        rule_id="temporal_logic.swap_predicate_kind",
                        metadata={
                            "path": [*full_path, "predicate"],
                            "from": predicate,
                            "to": pred_swap,
                        },
                    )
                )
            constant = node.get("constant")
            if type(constant) is int:
                for delta in (-1, 1):
                    updated = i64_add(constant, delta)
                    if updated is None:
                        continue
                    mutated_node = dict(node)
                    mutated_node["constant"] = updated
                    candidates.append(
                        candidate(
                            set_at_path(spec_dict, full_path, mutated_node),
                            mutant_kind="temporal_logic_constant_mutation",
                            rule_id=(
                                "temporal_logic.constant_"
                                f"{'minus' if delta < 0 else 'plus'}_one"
                            ),
                            metadata={
                                "path": [*full_path, "constant"],
                                "delta": delta,
                            },
                        )
                    )

        if op in unary_ops and isinstance(node.get("child"), dict):
            candidates.append(
                candidate(
                    set_at_path(spec_dict, full_path, node["child"]),
                    mutant_kind="temporal_logic_structure_mutation",
                    rule_id="temporal_logic.prune_unary_node",
                    metadata={"path": list(full_path), "op": op},
                )
            )
        if op in binary_ops:
            left = node.get("left")
            right = node.get("right")
            if isinstance(left, dict):
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, full_path, left),
                        mutant_kind="temporal_logic_structure_mutation",
                        rule_id="temporal_logic.prune_binary_to_left",
                        metadata={"path": list(full_path), "op": op},
                    )
                )
            if isinstance(right, dict):
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, full_path, right),
                        mutant_kind="temporal_logic_structure_mutation",
                        rule_id="temporal_logic.prune_binary_to_right",
                        metadata={"path": list(full_path), "op": op},
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
