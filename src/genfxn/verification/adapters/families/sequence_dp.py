from __future__ import annotations

from typing import Any

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.sequence_dp.eval import eval_sequence_dp
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

FAMILY = "sequence_dp"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, dict):
        raise TypeError("sequence_dp input must be dict(a,b)")
    a = input_value.get("a")
    b = input_value.get("b")
    if not isinstance(a, list) or not isinstance(b, list):
        raise TypeError("sequence_dp input must include list a/b")
    return eval_sequence_dp(spec_obj, a, b)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    value_range = range_from_axes(axes, "value_range", DEFAULT_INT_RANGE)
    len_a_range = nonnegative_range(
        range_from_axes(axes, "len_a_range", (0, 20))
    )
    len_b_range = nonnegative_range(
        range_from_axes(axes, "len_b_range", (0, 20))
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

    generated = st.fixed_dictionaries(
        {
            "a": st.lists(
                int_value_strategy,
                min_size=len_a_range[0],
                max_size=len_a_range[1],
            ),
            "b": st.lists(
                int_value_strategy,
                min_size=len_b_range[0],
                max_size=len_b_range[1],
            ),
        }
    )

    edge_cases = [
        {"a": [], "b": []},
        {"a": [0], "b": [0]},
        {"a": [1, -1], "b": [-1, 1]},
    ]

    return st.one_of(st.sampled_from(edge_cases), generated)


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
