from __future__ import annotations

from typing import Any

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.graph_queries.eval import eval_graph_queries
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import deterministic_rng

FAMILY = "graph_queries"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, dict):
        raise TypeError("graph_queries input must be dict(src,dst)")
    src = input_value.get("src")
    dst = input_value.get("dst")
    if isinstance(src, bool) or isinstance(dst, bool):
        raise TypeError("graph_queries src/dst must be int")
    if not isinstance(src, int) or not isinstance(dst, int):
        raise TypeError("graph_queries src/dst must be int")
    return eval_graph_queries(spec_obj, src, dst)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,  # noqa: ARG001
    seed: int,
) -> SearchStrategy[Any]:
    n_nodes = max(1, int(getattr(spec_obj, "n_nodes", 1)))
    node_strategy = st.integers(min_value=0, max_value=n_nodes - 1)

    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    edge_cases = [
        {"src": 0, "dst": 0},
        {"src": 0, "dst": n_nodes - 1},
        {"src": n_nodes - 1, "dst": 0},
        {"src": n_nodes - 1, "dst": n_nodes - 1},
    ]
    for _ in range(24):
        edge_cases.append(
            {
                "src": rng.randrange(n_nodes),
                "dst": rng.randrange(n_nodes),
            }
        )

    generated = st.fixed_dictionaries(
        {"src": node_strategy, "dst": node_strategy}
    )
    return st.one_of(st.sampled_from(edge_cases), generated)


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
)
