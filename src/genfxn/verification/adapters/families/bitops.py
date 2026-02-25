from __future__ import annotations

from typing import Any, cast

from hypothesis.strategies import SearchStrategy

from genfxn.bitops.eval import eval_bitops
from genfxn.core.spec_registry import validate_spec_for_family
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
    set_at_path,
)

FAMILY = "bitops"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if isinstance(input_value, bool) or not isinstance(input_value, int):
        raise TypeError("bitops input must be int")
    return eval_bitops(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    lo, hi = range_from_axes(axes, "value_range", DEFAULT_INT_RANGE)
    constants = collect_int_constants(to_spec_dict(spec_obj))
    width_bits = int(getattr(spec_obj, "width_bits", 8))
    mask = (1 << width_bits) - 1

    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    edge_values = [0, 1, -1, mask, mask + 1, -mask, lo, hi]
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

    width_bits = spec_dict.get("width_bits")
    if type(width_bits) is int:
        for delta in (-1, 1):
            updated = width_bits + delta
            if 1 <= updated <= 63:
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("width_bits",), updated),
                        mutant_kind="bitops_width_mutation",
                        rule_id=(
                            "bitops.width_bits_"
                            f"{'minus' if delta < 0 else 'plus'}_one"
                        ),
                        metadata={"path": ["width_bits"], "delta": delta},
                    )
                )

    operations = spec_dict.get("operations")
    if isinstance(operations, list):
        arg_ops = [
            "and_mask",
            "or_mask",
            "xor_mask",
            "shl",
            "shr_logical",
            "rotl",
            "rotr",
        ]
        noarg_ops = ["not", "popcount", "parity"]
        for index, op in enumerate(operations):
            if not isinstance(op, dict):
                continue
            current_op = op.get("op")
            if current_op in arg_ops:
                swap_to = "xor_mask" if current_op != "xor_mask" else "and_mask"
                mutated_op = dict(op)
                mutated_op["op"] = swap_to
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict, ("operations", index), mutated_op
                        ),
                        mutant_kind="bitops_operation_mutation",
                        rule_id="bitops.swap_arg_operation",
                        metadata={
                            "path": ["operations", index, "op"],
                            "from": current_op,
                            "to": swap_to,
                        },
                    )
                )
                to_noarg = "not"
                mutated_noarg = dict(op)
                mutated_noarg["op"] = to_noarg
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            ("operations", index),
                            mutated_noarg,
                        ),
                        mutant_kind="bitops_operation_mutation",
                        rule_id="bitops.arg_to_noarg_operation",
                        metadata={
                            "path": ["operations", index, "op"],
                            "from": current_op,
                            "to": to_noarg,
                        },
                    )
                )
            elif current_op in noarg_ops:
                mutated_op = dict(op)
                mutated_op["op"] = "xor_mask"
                mutated_op["arg"] = 1
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict, ("operations", index), mutated_op
                        ),
                        mutant_kind="bitops_operation_mutation",
                        rule_id="bitops.noarg_to_arg_operation",
                        metadata={
                            "path": ["operations", index, "op"],
                            "from": current_op,
                            "to": "xor_mask",
                        },
                    )
                )

            arg = op.get("arg")
            if type(arg) is int:
                for delta in (-1, 1):
                    updated = i64_add(arg, delta)
                    if updated is None:
                        continue
                    mutated_op = dict(op)
                    mutated_op["arg"] = updated
                    candidates.append(
                        candidate(
                            set_at_path(
                                spec_dict,
                                ("operations", index),
                                mutated_op,
                            ),
                            mutant_kind="bitops_arg_mutation",
                            rule_id=(
                                "bitops.arg_"
                                f"{'minus' if delta < 0 else 'plus'}_one"
                            ),
                            metadata={
                                "path": ["operations", index, "arg"],
                                "delta": delta,
                            },
                        )
                    )

        if len(operations) > 1:
            for index in range(len(operations)):
                mutated = list(operations)
                mutated.pop(index)
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("operations",), mutated),
                        mutant_kind="bitops_structural_mutation",
                        rule_id="bitops.remove_operation",
                        metadata={
                            "path": ["operations"],
                            "removed_index": index,
                        },
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
