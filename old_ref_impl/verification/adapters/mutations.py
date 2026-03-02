from __future__ import annotations

import copy
import json
import random
from collections.abc import Callable, Iterable
from hashlib import sha256
from typing import Any

from genfxn.verification.adapters.base import (
    Layer3Mode,
    Layer3MutantCandidate,
)

I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1


def stable_spec_hash(spec: Any) -> str:
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def derived_mode_seed(
    *,
    task_id: str,
    family: str,
    seed: int,
    mode: Layer3Mode,
) -> int:
    digest = sha256(
        f"{task_id}:{family}:layer3:{seed}:{mode}".encode()
    ).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def i64_add(value: int, delta: int) -> int | None:
    result = value + delta
    if result < I64_MIN or result > I64_MAX:
        return None
    return result


def candidate(
    mutant_spec: dict[str, Any],
    *,
    mutant_kind: str,
    rule_id: str,
    metadata: dict[str, Any] | None = None,
) -> Layer3MutantCandidate:
    return Layer3MutantCandidate(
        mutant_spec=mutant_spec,
        mutant_kind=mutant_kind,
        rule_id=rule_id,
        metadata=metadata or {},
    )


def set_at_path(
    root: dict[str, Any],
    path: tuple[Any, ...],
    value: Any,
) -> dict[str, Any]:
    out = copy.deepcopy(root)
    if not path:
        if isinstance(value, dict):
            return copy.deepcopy(value)
        raise ValueError("root replacement must be dict")

    node: Any = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return out


def remove_list_item_at_path(
    root: dict[str, Any],
    *,
    list_path: tuple[Any, ...],
    index: int,
) -> dict[str, Any]:
    out = copy.deepcopy(root)
    node: Any = out
    for key in list_path:
        node = node[key]
    if not isinstance(node, list):
        raise ValueError(f"path {list_path!r} does not point to list")
    node.pop(index)
    return out


def walk_nodes(
    value: Any,
    *,
    path: tuple[Any, ...] = (),
) -> Iterable[tuple[tuple[Any, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_nodes(child, path=(*path, key))
        return
    if isinstance(value, list):
        for idx, child in enumerate(value):
            yield from walk_nodes(child, path=(*path, idx))


def _partition_for_mode(
    candidates: list[Layer3MutantCandidate],
    *,
    mode: Layer3Mode,
) -> list[Layer3MutantCandidate]:
    ordered = sorted(
        candidates,
        key=lambda item: (
            item.rule_id,
            stable_spec_hash(item.mutant_spec),
            item.mutant_kind,
        ),
    )
    selected: list[Layer3MutantCandidate] = []
    for index, item in enumerate(ordered):
        is_train_slot = index % 2 == 0
        if mode == "train" and is_train_slot:
            selected.append(item)
        if mode == "heldout" and not is_train_slot:
            selected.append(item)
    return selected


def finalize_candidates(
    candidates: list[Layer3MutantCandidate],
    *,
    validate_spec: Callable[[dict[str, Any]], Any],
    original_spec: dict[str, Any],
    task_id: str,
    family: str,
    seed: int,
    mode: Layer3Mode,
    budget: int,
) -> list[Layer3MutantCandidate]:
    if budget <= 0 or not candidates:
        return []

    original_hash = stable_spec_hash(original_spec)
    deduped: list[Layer3MutantCandidate] = []
    seen_hashes = {original_hash}
    for item in candidates:
        mutant_hash = stable_spec_hash(item.mutant_spec)
        if mutant_hash in seen_hashes:
            continue
        try:
            validate_spec(item.mutant_spec)
        except Exception:
            continue
        seen_hashes.add(mutant_hash)
        deduped.append(item)

    partition = _partition_for_mode(deduped, mode=mode)
    if not partition:
        return []

    rng = random.Random(
        derived_mode_seed(
            task_id=task_id,
            family=family,
            seed=seed,
            mode=mode,
        )
    )
    shuffled = list(partition)
    rng.shuffle(shuffled)
    return shuffled[:budget]


def mutate_core_predicate(
    predicate: dict[str, Any],
) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
    kind = predicate.get("kind")
    results: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    if kind == "lt":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "le"
        results.append((mutated, "pred_lt_to_le", {"from": "lt", "to": "le"}))
    elif kind == "le":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "lt"
        results.append((mutated, "pred_le_to_lt", {"from": "le", "to": "lt"}))
    elif kind == "gt":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "ge"
        results.append((mutated, "pred_gt_to_ge", {"from": "gt", "to": "ge"}))
    elif kind == "ge":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "gt"
        results.append((mutated, "pred_ge_to_gt", {"from": "ge", "to": "gt"}))
    elif kind == "and":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "or"
        results.append((mutated, "pred_and_to_or", {"from": "and", "to": "or"}))
    elif kind == "or":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "and"
        results.append((mutated, "pred_or_to_and", {"from": "or", "to": "and"}))
    elif kind == "even":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "odd"
        results.append(
            (mutated, "pred_even_to_odd", {"from": "even", "to": "odd"})
        )
    elif kind == "odd":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "even"
        results.append(
            (mutated, "pred_odd_to_even", {"from": "odd", "to": "even"})
        )

    value = predicate.get("value")
    if type(value) is int:
        low = i64_add(value, -1)
        high = i64_add(value, 1)
        if low is not None:
            mutated = copy.deepcopy(predicate)
            mutated["value"] = low
            results.append((mutated, "pred_value_minus_one", {"delta": -1}))
        if high is not None:
            mutated = copy.deepcopy(predicate)
            mutated["value"] = high
            results.append((mutated, "pred_value_plus_one", {"delta": 1}))

    divisor = predicate.get("divisor")
    if type(divisor) is int:
        if divisor > 1:
            mutated = copy.deepcopy(predicate)
            mutated["divisor"] = divisor - 1
            results.append((mutated, "pred_divisor_minus_one", {"delta": -1}))
        if divisor < I64_MAX:
            mutated = copy.deepcopy(predicate)
            mutated["divisor"] = divisor + 1
            results.append((mutated, "pred_divisor_plus_one", {"delta": 1}))

    remainder = predicate.get("remainder")
    if type(divisor) is int and type(remainder) is int and divisor > 0:
        mutated = copy.deepcopy(predicate)
        mutated["remainder"] = (remainder + 1) % divisor
        results.append((mutated, "pred_remainder_roll", {}))

    return results


def mutate_core_transform(
    transform: dict[str, Any],
) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
    kind = transform.get("kind")
    results: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    if kind == "identity":
        mutated = copy.deepcopy(transform)
        mutated["kind"] = "negate"
        results.append(
            (
                mutated,
                "transform_identity_to_negate",
                {"from": "identity", "to": "negate"},
            )
        )
    elif kind == "negate":
        mutated = copy.deepcopy(transform)
        mutated["kind"] = "identity"
        results.append(
            (
                mutated,
                "transform_negate_to_identity",
                {"from": "negate", "to": "identity"},
            )
        )

    offset = transform.get("offset")
    if type(offset) is int:
        low = i64_add(offset, -1)
        high = i64_add(offset, 1)
        if low is not None:
            mutated = copy.deepcopy(transform)
            mutated["offset"] = low
            results.append((mutated, "transform_offset_minus_one", {}))
        if high is not None:
            mutated = copy.deepcopy(transform)
            mutated["offset"] = high
            results.append((mutated, "transform_offset_plus_one", {}))

    factor = transform.get("factor")
    if type(factor) is int:
        low = i64_add(factor, -1)
        high = i64_add(factor, 1)
        if low is not None:
            mutated = copy.deepcopy(transform)
            mutated["factor"] = low
            results.append((mutated, "transform_factor_minus_one", {}))
        if high is not None:
            mutated = copy.deepcopy(transform)
            mutated["factor"] = high
            results.append((mutated, "transform_factor_plus_one", {}))

    low_val = transform.get("low")
    high_val = transform.get("high")
    if type(low_val) is int:
        nxt = i64_add(low_val, 1)
        if nxt is not None:
            mutated = copy.deepcopy(transform)
            mutated["low"] = nxt
            results.append((mutated, "transform_clip_low_plus_one", {}))
    if type(high_val) is int:
        nxt = i64_add(high_val, -1)
        if nxt is not None:
            mutated = copy.deepcopy(transform)
            mutated["high"] = nxt
            results.append((mutated, "transform_clip_high_minus_one", {}))

    return results


def remove_pipeline_step_variants(
    pipeline_steps: list[dict[str, Any]],
) -> list[tuple[list[dict[str, Any]], str, dict[str, Any]]]:
    if len(pipeline_steps) <= 2:
        return []
    variants: list[tuple[list[dict[str, Any]], str, dict[str, Any]]] = []
    for index in range(len(pipeline_steps)):
        mutated = list(pipeline_steps)
        mutated.pop(index)
        variants.append(
            (
                mutated,
                "pipeline_remove_step",
                {"removed_index": index},
            )
        )
    return variants


def mutate_string_predicate(
    predicate: dict[str, Any],
) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
    kind = predicate.get("kind")
    results: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    if kind == "starts_with":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "contains"
        results.append((mutated, "str_pred_starts_to_contains", {}))
    elif kind == "ends_with":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "contains"
        results.append((mutated, "str_pred_ends_to_contains", {}))
    elif kind == "contains":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "starts_with"
        results.append((mutated, "str_pred_contains_to_starts", {}))
    elif kind == "is_upper":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "is_lower"
        results.append((mutated, "str_pred_upper_to_lower", {}))
    elif kind == "is_lower":
        mutated = copy.deepcopy(predicate)
        mutated["kind"] = "is_upper"
        results.append((mutated, "str_pred_lower_to_upper", {}))

    op = predicate.get("op")
    if op == "lt":
        mutated = copy.deepcopy(predicate)
        mutated["op"] = "le"
        results.append((mutated, "str_pred_len_lt_to_le", {}))
    elif op == "le":
        mutated = copy.deepcopy(predicate)
        mutated["op"] = "lt"
        results.append((mutated, "str_pred_len_le_to_lt", {}))
    elif op == "gt":
        mutated = copy.deepcopy(predicate)
        mutated["op"] = "ge"
        results.append((mutated, "str_pred_len_gt_to_ge", {}))
    elif op == "ge":
        mutated = copy.deepcopy(predicate)
        mutated["op"] = "gt"
        results.append((mutated, "str_pred_len_ge_to_gt", {}))
    elif op == "eq":
        mutated = copy.deepcopy(predicate)
        mutated["op"] = "ge"
        results.append((mutated, "str_pred_len_eq_to_ge", {}))

    value = predicate.get("value")
    if type(value) is int:
        if value > 0:
            mutated = copy.deepcopy(predicate)
            mutated["value"] = value - 1
            results.append((mutated, "str_pred_value_minus_one", {}))
        mutated = copy.deepcopy(predicate)
        mutated["value"] = value + 1
        results.append((mutated, "str_pred_value_plus_one", {}))

    return results


def mutate_string_transform(
    transform: dict[str, Any],
) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
    kind = transform.get("kind")
    results: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
    if kind == "identity":
        mutated = copy.deepcopy(transform)
        mutated["kind"] = "reverse"
        results.append((mutated, "str_transform_identity_to_reverse", {}))
    elif kind == "lowercase":
        mutated = copy.deepcopy(transform)
        mutated["kind"] = "uppercase"
        results.append((mutated, "str_transform_lower_to_upper", {}))
    elif kind == "uppercase":
        mutated = copy.deepcopy(transform)
        mutated["kind"] = "lowercase"
        results.append((mutated, "str_transform_upper_to_lower", {}))
    elif kind == "prepend":
        mutated = copy.deepcopy(transform)
        prefix = str(transform.get("prefix", ""))
        mutated["prefix"] = f"{prefix}x"
        results.append((mutated, "str_transform_prepend_extend", {}))
    elif kind == "append":
        mutated = copy.deepcopy(transform)
        suffix = str(transform.get("suffix", ""))
        mutated["suffix"] = f"{suffix}x"
        results.append((mutated, "str_transform_append_extend", {}))
    elif kind == "replace":
        mutated = copy.deepcopy(transform)
        old_value = str(transform.get("old", ""))
        mutated["old"] = f"{old_value}x" if old_value else "x"
        results.append((mutated, "str_transform_replace_old_shift", {}))
    return results
