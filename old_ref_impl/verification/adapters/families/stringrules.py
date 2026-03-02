from __future__ import annotations

from typing import Any, cast

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.stringrules.eval import eval_stringrules
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    ASCII_ALPHABET,
    deterministic_rng,
    nonnegative_range,
    range_from_axes,
)
from genfxn.verification.adapters.mutations import (
    candidate,
    finalize_candidates,
    mutate_string_predicate,
    mutate_string_transform,
    set_at_path,
    walk_nodes,
)

FAMILY = "stringrules"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, str):
        raise TypeError("stringrules input must be str")
    return eval_stringrules(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    lo, hi = nonnegative_range(
        range_from_axes(axes, "string_length_range", (0, 20))
    )
    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    edge_values = ["", "a", "A", "0", "abc", "ABC", "a1B2", "  spaced  "]
    for _ in range(24):
        n = rng.randint(lo, hi)
        edge_values.append(
            "".join(rng.choice(ASCII_ALPHABET) for _ in range(n))
        )

    return st.one_of(
        st.sampled_from(edge_values),
        st.text(alphabet=ASCII_ALPHABET, min_size=lo, max_size=hi),
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

    predicate_kinds = {
        "starts_with",
        "ends_with",
        "contains",
        "is_alpha",
        "is_digit",
        "is_upper",
        "is_lower",
        "length_cmp",
        "not",
        "and",
        "or",
    }
    transform_kinds = {
        "identity",
        "lowercase",
        "uppercase",
        "capitalize",
        "swapcase",
        "reverse",
        "replace",
        "strip",
        "prepend",
        "append",
        "pipeline",
    }

    for path, node in walk_nodes(spec_dict):
        if not isinstance(node, dict):
            continue
        kind = node.get("kind")
        if kind in predicate_kinds:
            for mutated_predicate, rule_id, metadata in mutate_string_predicate(
                node
            ):
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            path,
                            mutated_predicate,
                        ),
                        mutant_kind="stringrules_predicate_mutation",
                        rule_id=f"stringrules.{rule_id}",
                        metadata={"path": list(path), **metadata},
                    )
                )
        if kind in transform_kinds:
            for mutated_transform, rule_id, metadata in mutate_string_transform(
                node
            ):
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            path,
                            mutated_transform,
                        ),
                        mutant_kind="stringrules_transform_mutation",
                        rule_id=f"stringrules.{rule_id}",
                        metadata={"path": list(path), **metadata},
                    )
                )

    rules = spec_dict.get("rules")
    if isinstance(rules, list) and len(rules) > 1:
        for idx in range(len(rules)):
            removed = list(rules)
            removed.pop(idx)
            candidates.append(
                candidate(
                    set_at_path(spec_dict, ("rules",), removed),
                    mutant_kind="stringrules_structural_mutation",
                    rule_id="stringrules.remove_rule",
                    metadata={"path": ["rules"], "removed_index": idx},
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
