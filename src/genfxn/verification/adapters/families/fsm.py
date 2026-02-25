from __future__ import annotations

from typing import Any, cast

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.fsm.eval import eval_fsm
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
    mutate_core_predicate,
    set_at_path,
    walk_nodes,
)

FAMILY = "fsm"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("fsm input must be list[int]")
    return eval_fsm(spec_obj, input_value)


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

    output_mode = spec_dict.get("output_mode")
    output_alt = {
        "final_state_id": "accept_bool",
        "accept_bool": "transition_count",
        "transition_count": "final_state_id",
    }.get(output_mode)
    if output_alt is not None:
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("output_mode",), output_alt),
                mutant_kind="fsm_mode_mutation",
                rule_id="fsm.output_mode_swap",
                metadata={"path": ["output_mode"], "to": output_alt},
            )
        )

    policy = spec_dict.get("undefined_transition_policy")
    policy_alt = {
        "sink": "stay",
        "stay": "error",
        "error": "sink",
    }.get(policy)
    if policy_alt is not None:
        candidates.append(
            candidate(
                set_at_path(
                    spec_dict,
                    ("undefined_transition_policy",),
                    policy_alt,
                ),
                mutant_kind="fsm_policy_mutation",
                rule_id="fsm.undefined_transition_policy_swap",
                metadata={
                    "path": ["undefined_transition_policy"],
                    "to": policy_alt,
                },
            )
        )

    states = spec_dict.get("states")
    state_ids: list[int] = []
    if isinstance(states, list):
        for index, state in enumerate(states):
            if not isinstance(state, dict):
                continue
            state_id = state.get("id")
            if type(state_id) is int:
                state_ids.append(state_id)
            is_accept = state.get("is_accept")
            if isinstance(is_accept, bool):
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            ("states", index, "is_accept"),
                            not is_accept,
                        ),
                        mutant_kind="fsm_accept_mutation",
                        rule_id="fsm.flip_state_accept_flag",
                        metadata={
                            "path": ["states", index, "is_accept"],
                            "state_id": state_id,
                        },
                    )
                )

            transitions = state.get("transitions")
            if not isinstance(transitions, list):
                continue
            for t_index, transition in enumerate(transitions):
                if not isinstance(transition, dict):
                    continue
                target = transition.get("target_state_id")
                if type(target) is int:
                    for other_id in state_ids:
                        if other_id == target:
                            continue
                        candidates.append(
                            candidate(
                                set_at_path(
                                    spec_dict,
                                    (
                                        "states",
                                        index,
                                        "transitions",
                                        t_index,
                                        "target_state_id",
                                    ),
                                    other_id,
                                ),
                                mutant_kind="fsm_transition_target_mutation",
                                rule_id="fsm.swap_transition_target",
                                metadata={
                                    "path": [
                                        "states",
                                        index,
                                        "transitions",
                                        t_index,
                                        "target_state_id",
                                    ],
                                    "from": target,
                                    "to": other_id,
                                },
                            )
                        )
                        break

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
    for path, node in walk_nodes(spec_dict):
        if not isinstance(node, dict):
            continue
        if node.get("kind") not in predicate_kinds:
            continue
        for mutated_predicate, rule_id, metadata in mutate_core_predicate(node):
            candidates.append(
                candidate(
                    set_at_path(
                        spec_dict,
                        path,
                        mutated_predicate,
                    ),
                    mutant_kind="fsm_predicate_mutation",
                    rule_id=f"fsm.{rule_id}",
                    metadata={"path": list(path), **metadata},
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
