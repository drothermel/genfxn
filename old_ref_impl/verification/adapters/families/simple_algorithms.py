from __future__ import annotations

from typing import Any, cast

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.simple_algorithms.eval import eval_simple_algorithms
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
    mutate_core_predicate,
    mutate_core_transform,
    set_at_path,
    walk_nodes,
)

FAMILY = "simple_algorithms"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("simple_algorithms input must be list[int]")
    return eval_simple_algorithms(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    value_range = range_from_axes(axes, "value_range", DEFAULT_INT_RANGE)
    length_range = nonnegative_range(
        range_from_axes(
            axes,
            "list_length_range",
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
    template = spec_dict.get("template")

    tie_break = spec_dict.get("tie_break")
    if tie_break == "smallest":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("tie_break",), "first_seen"),
                mutant_kind="simple_algorithms_mode_mutation",
                rule_id="simple_algorithms.tie_break_smallest_to_first_seen",
                metadata={"path": ["tie_break"]},
            )
        )
    elif tie_break == "first_seen":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("tie_break",), "smallest"),
                mutant_kind="simple_algorithms_mode_mutation",
                rule_id="simple_algorithms.tie_break_first_seen_to_smallest",
                metadata={"path": ["tie_break"]},
            )
        )

    counting_mode = spec_dict.get("counting_mode")
    if counting_mode == "all_indices":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("counting_mode",), "unique_values"),
                mutant_kind="simple_algorithms_mode_mutation",
                rule_id="simple_algorithms.counting_mode_all_indices_to_unique_values",
                metadata={"path": ["counting_mode"]},
            )
        )
    elif counting_mode == "unique_values":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("counting_mode",), "all_indices"),
                mutant_kind="simple_algorithms_mode_mutation",
                rule_id="simple_algorithms.counting_mode_unique_values_to_all_indices",
                metadata={"path": ["counting_mode"]},
            )
        )

    for field_name in (
        "target",
        "k",
        "empty_default",
        "tie_default",
        "invalid_k_default",
        "no_result_default",
        "short_list_default",
    ):
        value = spec_dict.get(field_name)
        if type(value) is not int:
            continue
        for delta in (-1, 1):
            updated = i64_add(value, delta)
            if updated is None:
                continue
            if field_name == "k" and updated < 1:
                continue
            candidates.append(
                candidate(
                    set_at_path(spec_dict, (field_name,), updated),
                    mutant_kind="simple_algorithms_numeric_mutation",
                    rule_id=(
                        f"simple_algorithms.{field_name}_"
                        f"{'minus' if delta < 0 else 'plus'}_one"
                    ),
                    metadata={"path": [field_name], "delta": delta},
                )
            )

    predicate_kinds = {
        "even",
        "odd",
        "lt",
        "le",
        "gt",
        "ge",
        "mod_eq",
        "in_set",
        "not",
        "and",
        "or",
    }
    transform_kinds = {
        "identity",
        "abs",
        "shift",
        "clip",
        "negate",
        "scale",
        "pipeline",
    }
    for path, node in walk_nodes(spec_dict):
        if not isinstance(node, dict):
            continue
        kind = node.get("kind")
        if kind in predicate_kinds:
            for mutated_predicate, rule_id, metadata in mutate_core_predicate(
                node
            ):
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            path,
                            mutated_predicate,
                        ),
                        mutant_kind="simple_algorithms_predicate_mutation",
                        rule_id=f"simple_algorithms.{rule_id}",
                        metadata={"path": list(path), **metadata},
                    )
                )
        if kind in transform_kinds:
            for mutated_transform, rule_id, metadata in mutate_core_transform(
                node
            ):
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            path,
                            mutated_transform,
                        ),
                        mutant_kind="simple_algorithms_transform_mutation",
                        rule_id=f"simple_algorithms.{rule_id}",
                        metadata={"path": list(path), **metadata},
                    )
                )

    # Family-specific semantic nudge for max_window_sum.
    if template == "max_window_sum":
        current = spec_dict.get("k")
        if type(current) is int and current > 1:
            candidates.append(
                candidate(
                    set_at_path(spec_dict, ("k",), max(1, current // 2)),
                    mutant_kind="simple_algorithms_window_mutation",
                    rule_id="simple_algorithms.max_window_k_halve",
                    metadata={"path": ["k"]},
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
