from __future__ import annotations

from typing import Any

from hypothesis.strategies import SearchStrategy

from genfxn.bitops.eval import eval_bitops
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


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
