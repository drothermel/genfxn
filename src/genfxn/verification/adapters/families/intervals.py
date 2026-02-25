from __future__ import annotations

from typing import Any

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.intervals.eval import eval_intervals
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    DEFAULT_INT_RANGE,
    collect_int_constants,
    deterministic_rng,
    nonnegative_range,
    range_from_axes,
)
from genfxn.verification.adapters.families._shared import (
    choose_extra_int_edges,
    int_strategy,
    to_spec_dict,
)

FAMILY = "intervals"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("intervals input must be list[tuple[int,int]]")
    return eval_intervals(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    endpoint_range = range_from_axes(axes, "endpoint_range", DEFAULT_INT_RANGE)
    list_length_range = nonnegative_range(
        range_from_axes(axes, "n_intervals_range", (0, 10))
    )
    lo, hi = endpoint_range
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
            count=40,
        )
    )
    point_strategy = int_strategy(lo=lo, hi=hi, edge_values=int_values)
    pair_strategy = st.tuples(point_strategy, point_strategy)
    generated = st.lists(
        pair_strategy,
        min_size=list_length_range[0],
        max_size=list_length_range[1],
    )

    edge_cases: list[list[tuple[int, int]]] = [
        [],
        [(0, 0)],
        [(0, 1)],
        [(1, 0)],
        [(lo, hi)],
        [(hi, lo)],
    ]
    if constants:
        c = constants[0]
        edge_cases.append([(c - 1, c), (c, c + 1)])

    return st.one_of(st.sampled_from(edge_cases), generated)


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
