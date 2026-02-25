from __future__ import annotations

from typing import Any

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.stringrules.eval import eval_stringrules
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    ASCII_ALPHABET,
    deterministic_rng,
    nonnegative_range,
    range_from_axes,
)

FAMILY = "stringrules"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, str):
        raise TypeError("stringrules input must be str")
    return eval_stringrules(spec_obj, input_value)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    lo, hi = nonnegative_range(
        range_from_axes(axes, "string_length_range", (0, 20))
    )
    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    edge_values = ["", "a", "A", "0", "abc", "ABC", "a1B2", "  spaced  "]
    for _ in range(24):
        n = rng.randint(lo, hi)
        edge_values.append(
            "".join(rng.choice(ASCII_ALPHABET) for _ in range(n))
        )

    return st.one_of(
        st.sampled_from(edge_values),
        st.text(alphabet=ASCII_ALPHABET, min_size=lo, max_size=hi),
    )


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
