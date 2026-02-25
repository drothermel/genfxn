from __future__ import annotations

from typing import Any

from hypothesis.strategies import SearchStrategy

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


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
