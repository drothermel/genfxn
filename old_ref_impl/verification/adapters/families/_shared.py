from __future__ import annotations

from typing import Any

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.verification.adapters.common import unique_list


def int_strategy(
    *,
    lo: int,
    hi: int,
    edge_values: list[int],
) -> SearchStrategy[int]:
    deduped = unique_list(edge_values)
    if deduped:
        return st.one_of(st.sampled_from(deduped), st.integers(lo, hi))
    return st.integers(lo, hi)


def int_list_strategy(
    *,
    int_value_strategy: SearchStrategy[int],
    length_range: tuple[int, int],
    edge_lists: list[list[int]],
) -> SearchStrategy[list[int]]:
    lo, hi = length_range
    generated = st.lists(int_value_strategy, min_size=lo, max_size=hi)
    deduped_edges = unique_list(edge_lists)
    if deduped_edges:
        return st.one_of(st.sampled_from(deduped_edges), generated)
    return generated


def choose_extra_int_edges(
    *,
    lo: int,
    hi: int,
    constants: list[int],
    rng,
    count: int,
) -> list[int]:
    values: list[int] = []
    if lo <= hi:
        for _ in range(count):
            if constants and rng.random() < 0.6:
                c = rng.choice(constants)
                values.append(c)
                values.append(c - 1)
                values.append(c + 1)
            else:
                values.append(rng.randint(lo, hi))
    return values


def to_spec_dict(spec_obj: Any) -> dict[str, Any]:
    model_dump = getattr(spec_obj, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    return {}
