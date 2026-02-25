from __future__ import annotations

import hashlib
import json
import random
import string
from typing import Any

from hypothesis import HealthCheck, Phase, given, seed, settings
from hypothesis.strategies import SearchStrategy

ASCII_ALPHABET = string.ascii_letters + string.digits + " _-"
DEFAULT_INT_RANGE = (-100, 100)
DEFAULT_LIST_LENGTH_RANGE = (0, 20)


def seed_for_task_layer(
    task_id: str,
    layer_name: str,
    seed_value: int = 0,
    *,
    family: str | None = None,
) -> int:
    family_part = f":{family}" if family is not None else ""
    digest = hashlib.sha256(
        f"{task_id}{family_part}:{layer_name}:{seed_value}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def deterministic_rng(
    task_id: str,
    *,
    family: str,
    seed_value: int,
    layer_name: str,
) -> random.Random:
    return random.Random(
        seed_for_task_layer(
            task_id,
            layer_name,
            seed_value,
            family=family,
        )
    )


def collect_int_constants(value: Any) -> list[int]:
    constants: list[int] = []

    def _visit(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int):
            constants.append(node)
            return
        if isinstance(node, list | tuple | set | frozenset):
            for child in node:
                _visit(child)
            return
        if isinstance(node, dict):
            for child in node.values():
                _visit(child)

    _visit(value)
    return sorted(set(constants))


def range_from_axes(
    axes: dict[str, Any] | None,
    key: str,
    default: tuple[int, int],
) -> tuple[int, int]:
    if axes is None:
        return default
    value = axes.get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default

    lo, hi = value
    if isinstance(lo, bool) or isinstance(hi, bool):
        return default
    if not isinstance(lo, int) or not isinstance(hi, int):
        return default
    if lo > hi:
        return default
    return lo, hi


def nonnegative_range(value: tuple[int, int]) -> tuple[int, int]:
    lo, hi = value
    lo = max(0, lo)
    hi = max(lo, hi)
    return lo, hi


def unique_list(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    deduped: list[Any] = []
    for value in values:
        key = canonical_key(value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def canonical_key(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except TypeError:
        return repr(value)


def sample_strategy_examples(
    strategy: SearchStrategy[Any],
    *,
    seed_value: int,
    max_examples: int,
) -> list[Any]:
    if max_examples <= 0:
        return []

    draws: list[Any] = []

    @seed(seed_value)
    @settings(
        max_examples=max_examples,
        phases=(Phase.generate,),
        derandomize=False,
        database=None,
        deadline=None,
        suppress_health_check=list(HealthCheck),
    )
    @given(strategy)
    def _collector(value: Any) -> None:
        draws.append(value)

    _collector()
    return draws
