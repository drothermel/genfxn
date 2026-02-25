from __future__ import annotations

from typing import Any, cast

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.stack_bytecode.eval import eval_stack_bytecode
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
)

FAMILY = "stack_bytecode"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("stack_bytecode input must be list[int]")
    return eval_stack_bytecode(spec_obj, input_value)


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

    max_steps = spec_dict.get("max_step_count")
    if type(max_steps) is int:
        for delta in (-1, 1):
            updated = i64_add(max_steps, delta)
            if updated is None or updated < 1:
                continue
            candidates.append(
                candidate(
                    set_at_path(spec_dict, ("max_step_count",), updated),
                    mutant_kind="stack_bytecode_runtime_mutation",
                    rule_id=(
                        "stack_bytecode.max_step_count_"
                        f"{'minus' if delta < 0 else 'plus'}_one"
                    ),
                    metadata={"path": ["max_step_count"], "delta": delta},
                )
            )

    jump_mode = spec_dict.get("jump_target_mode")
    if jump_mode == "error":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("jump_target_mode",), "clamp"),
                mutant_kind="stack_bytecode_mode_mutation",
                rule_id="stack_bytecode.jump_target_mode_error_to_clamp",
                metadata={"path": ["jump_target_mode"]},
            )
        )
    elif jump_mode == "clamp":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("jump_target_mode",), "wrap"),
                mutant_kind="stack_bytecode_mode_mutation",
                rule_id="stack_bytecode.jump_target_mode_clamp_to_wrap",
                metadata={"path": ["jump_target_mode"]},
            )
        )
    elif jump_mode == "wrap":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("jump_target_mode",), "error"),
                mutant_kind="stack_bytecode_mode_mutation",
                rule_id="stack_bytecode.jump_target_mode_wrap_to_error",
                metadata={"path": ["jump_target_mode"]},
            )
        )

    input_mode = spec_dict.get("input_mode")
    if input_mode == "direct":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("input_mode",), "cyclic"),
                mutant_kind="stack_bytecode_mode_mutation",
                rule_id="stack_bytecode.input_mode_direct_to_cyclic",
                metadata={"path": ["input_mode"]},
            )
        )
    elif input_mode == "cyclic":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("input_mode",), "direct"),
                mutant_kind="stack_bytecode_mode_mutation",
                rule_id="stack_bytecode.input_mode_cyclic_to_direct",
                metadata={"path": ["input_mode"]},
            )
        )

    program = spec_dict.get("program")
    if isinstance(program, list):
        op_swaps = {
            "add": "sub",
            "sub": "add",
            "mul": "add",
            "div": "mul",
            "jump_if_zero": "jump_if_nonzero",
            "jump_if_nonzero": "jump_if_zero",
            "gt": "lt",
            "lt": "gt",
            "eq": "is_zero",
            "is_zero": "eq",
        }
        for index, instruction in enumerate(program):
            if not isinstance(instruction, dict):
                continue
            op = instruction.get("op")
            swap = op_swaps.get(op)
            if swap is not None:
                mutated_instruction = dict(instruction)
                mutated_instruction["op"] = swap
                candidates.append(
                    candidate(
                        set_at_path(
                            spec_dict,
                            ("program", index),
                            mutated_instruction,
                        ),
                        mutant_kind="stack_bytecode_instruction_mutation",
                        rule_id="stack_bytecode.swap_instruction_op",
                        metadata={
                            "path": ["program", index, "op"],
                            "from": op,
                            "to": swap,
                        },
                    )
                )

            for field_name in ("value", "index", "target"):
                value = instruction.get(field_name)
                if type(value) is not int:
                    continue
                for delta in (-1, 1):
                    updated = i64_add(value, delta)
                    if updated is None:
                        continue
                    mutated_instruction = dict(instruction)
                    mutated_instruction[field_name] = updated
                    candidates.append(
                        candidate(
                            set_at_path(
                                spec_dict,
                                ("program", index),
                                mutated_instruction,
                            ),
                            mutant_kind="stack_bytecode_instruction_mutation",
                            rule_id=(
                                f"stack_bytecode.{field_name}_"
                                f"{'minus' if delta < 0 else 'plus'}_one"
                            ),
                            metadata={
                                "path": ["program", index, field_name],
                                "delta": delta,
                            },
                        )
                    )

        if len(program) > 1:
            for index in range(len(program)):
                mutated_program = list(program)
                removed = mutated_program.pop(index)
                if not any(
                    isinstance(item, dict) and item.get("op") == "halt"
                    for item in mutated_program
                ):
                    continue
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("program",), mutated_program),
                        mutant_kind="stack_bytecode_structural_mutation",
                        rule_id="stack_bytecode.remove_program_step",
                        metadata={
                            "path": ["program"],
                            "removed_index": index,
                            "removed_op": (
                                removed.get("op")
                                if isinstance(removed, dict)
                                else None
                            ),
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
