from __future__ import annotations

from typing import Any, cast

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.piecewise.eval import eval_piecewise
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    DEFAULT_INT_RANGE,
    collect_int_constants,
    deterministic_rng,
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
    mutate_core_predicate,
    set_at_path,
    walk_nodes,
)

FAMILY = "piecewise"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if isinstance(input_value, bool) or not isinstance(input_value, int):
        raise TypeError("piecewise input must be int")
    return eval_piecewise(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    lo, hi = range_from_axes(axes, "value_range", DEFAULT_INT_RANGE)
    constants = collect_int_constants(to_spec_dict(spec_obj))
    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    edge_values = [lo, hi, 0, 1, -1]
    for constant in constants[:16]:
        edge_values.extend([constant - 1, constant, constant + 1])
    edge_values.extend(
        choose_extra_int_edges(
            lo=lo,
            hi=hi,
            constants=constants,
            rng=rng,
            count=32,
        )
    )
    return int_strategy(lo=lo, hi=hi, edge_values=edge_values)


def _layer3_mutants(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    spec_dict: dict[str, Any],
    budget: int,
    seed: int,
    mode: str,
) -> list[Any]:
    candidates: list[Any] = []

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
                        mutant_kind="piecewise_predicate_mutation",
                        rule_id=f"piecewise.{rule_id}",
                        metadata={
                            "path": list(path),
                            **metadata,
                        },
                    )
                )

        if kind in {"affine", "quadratic", "abs", "mod"}:
            for field_name in ("a", "b", "c", "divisor"):
                raw_value = node.get(field_name)
                if type(raw_value) is not int:
                    continue
                for delta in (-1, 1):
                    updated = i64_add(raw_value, delta)
                    if updated is None:
                        continue
                    expr_mutant = dict(node)
                    expr_mutant[field_name] = updated
                    candidates.append(
                        candidate(
                            set_at_path(
                                spec_dict,
                                path,
                                expr_mutant,
                            ),
                            mutant_kind="piecewise_expression_mutation",
                            rule_id=(
                                f"piecewise.expr_{field_name}_"
                                f"{'minus' if delta < 0 else 'plus'}_one"
                            ),
                            metadata={
                                "path": list(path),
                                "field": field_name,
                                "delta": delta,
                            },
                        )
                    )

    branches = spec_dict.get("branches")
    if isinstance(branches, list) and len(branches) >= 2:
        swapped = list(branches)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("branches",), swapped),
                mutant_kind="piecewise_structural_mutation",
                rule_id="piecewise.swap_first_two_branches",
                metadata={"path": ["branches"]},
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
