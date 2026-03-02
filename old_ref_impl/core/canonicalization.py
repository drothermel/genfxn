from __future__ import annotations

import hashlib
from typing import Any

import srsly

from genfxn.core.codegen import _canonicalize_for_hash
from genfxn.core.spec_registry import validate_spec_for_family

SPEC_CANON_V1 = "spec_canon_v1"


def _stable_sort_key(value: Any) -> str:
    return srsly.json_dumps(_canonicalize_for_hash(value), sort_keys=True)


def _sort_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: mapping[key] for key in sorted(mapping)}


def _dedupe_sorted(values: list[Any]) -> list[Any]:
    ordered = sorted(values, key=_stable_sort_key)
    deduped: list[Any] = []
    previous: Any = None
    has_previous = False
    for value in ordered:
        if has_previous and value == previous:
            continue
        deduped.append(value)
        previous = value
        has_previous = True
    return deduped


def _is_identity_transform(value: Any) -> bool:
    return isinstance(value, dict) and value.get("kind") == "identity"


def _canonicalize_node(value: Any) -> Any:
    if isinstance(value, dict):
        kind = value.get("kind")
        op = value.get("op")

        if kind in {"and", "or"} and isinstance(value.get("operands"), list):
            operands = [
                _canonicalize_node(operand)
                for operand in value.get("operands", [])
            ]
            folded = _dedupe_sorted(operands)
            if len(folded) == 1:
                return folded[0]
            output = {
                key: _canonicalize_node(item)
                for key, item in value.items()
                if key != "operands"
            }
            output["operands"] = folded
            return _sort_mapping(output)

        if kind == "pipeline" and isinstance(value.get("steps"), list):
            steps = [_canonicalize_node(step) for step in value["steps"]]
            steps = [step for step in steps if not _is_identity_transform(step)]
            if not steps:
                return {"kind": "identity"}
            if len(steps) == 1:
                return steps[0]
            output = {
                key: _canonicalize_node(item)
                for key, item in value.items()
                if key != "steps"
            }
            output["steps"] = steps
            return _sort_mapping(output)

        if op in {"and", "or"} and "left" in value and "right" in value:
            left = _canonicalize_node(value["left"])
            right = _canonicalize_node(value["right"])
            if left == right:
                return left
            if _stable_sort_key(left) > _stable_sort_key(right):
                left, right = right, left
            output = {
                key: _canonicalize_node(item)
                for key, item in value.items()
                if key not in {"left", "right"}
            }
            output["left"] = left
            output["right"] = right
            return _sort_mapping(output)

        return _sort_mapping(
            {key: _canonicalize_node(item) for key, item in value.items()}
        )

    if isinstance(value, list):
        return [_canonicalize_node(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_canonicalize_node(item) for item in value)
    if isinstance(value, set):
        items = [_canonicalize_node(item) for item in value]
        return {"__set__": sorted(items, key=_stable_sort_key)}
    if isinstance(value, frozenset):
        items = [_canonicalize_node(item) for item in value]
        return {"__frozenset__": sorted(items, key=_stable_sort_key)}
    return value


def _normalize_graph_spec(spec: dict[str, Any]) -> dict[str, Any]:
    edges = spec.get("edges")
    if not isinstance(edges, list):
        return spec

    directed = bool(spec.get("directed", False))
    weighted = bool(spec.get("weighted", False))
    best_by_edge: dict[tuple[int, int], int] = {}

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        u = edge.get("u")
        v = edge.get("v")
        raw_weight = edge.get("w", 1)
        if not isinstance(u, int) or not isinstance(v, int):
            continue
        if not isinstance(raw_weight, int):
            continue

        eff_weight = raw_weight if weighted else 1
        if directed:
            key = (u, v)
        else:
            lo, hi = sorted((u, v))
            key = (lo, hi)

        prior = best_by_edge.get(key)
        if prior is None or eff_weight < prior:
            best_by_edge[key] = eff_weight

    normalized_edges = [
        {"u": u, "v": v, "w": w}
        for (u, v), w in sorted(
            best_by_edge.items(),
            key=lambda item: (item[0][0], item[0][1], item[1]),
        )
    ]

    output = dict(spec)
    output["edges"] = normalized_edges
    return output


def _normalize_fsm_spec(spec: dict[str, Any]) -> dict[str, Any]:
    states = spec.get("states")
    if not isinstance(states, list):
        return spec

    output = dict(spec)
    output["states"] = sorted(
        states,
        key=lambda state: state.get("id", 0) if isinstance(state, dict) else 0,
    )
    return output


def canonicalize_spec_for_hash(family: str, spec: Any) -> Any:
    validated_spec = validate_spec_for_family(family, spec)
    if hasattr(validated_spec, "model_dump") and callable(
        validated_spec.model_dump
    ):
        base: Any = validated_spec.model_dump(mode="python")
    else:
        base = validated_spec

    if not isinstance(base, dict):
        raise TypeError("Spec must validate to a dictionary-like object")

    normalized = dict(base)
    if family == "graph_queries":
        normalized = _normalize_graph_spec(normalized)
    elif family == "fsm":
        normalized = _normalize_fsm_spec(normalized)

    return _canonicalize_node(normalized)


def canonical_spec_bytes(family: str, spec: Any) -> bytes:
    canonical_spec = canonicalize_spec_for_hash(family, spec)
    payload = {
        "family": family,
        "spec": canonical_spec,
        "version": SPEC_CANON_V1,
    }
    return srsly.json_dumps(
        _canonicalize_for_hash(payload), sort_keys=True
    ).encode("utf-8")


def compute_spec_id(family: str, spec: Any) -> str:
    return hashlib.sha256(canonical_spec_bytes(family, spec)).hexdigest()
