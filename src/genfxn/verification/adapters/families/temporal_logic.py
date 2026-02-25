from __future__ import annotations

from typing import Any

from hypothesis.strategies import SearchStrategy

from genfxn.temporal_logic.eval import eval_temporal_logic
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

FAMILY = "temporal_logic"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, list):
        raise TypeError("temporal_logic input must be list[int]")
    return eval_temporal_logic(spec_obj, input_value)


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


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
