from __future__ import annotations

from typing import Any, cast

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.graph_queries.eval import eval_graph_queries
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import deterministic_rng
from genfxn.verification.adapters.mutations import (
    candidate,
    finalize_candidates,
    i64_add,
    set_at_path,
)

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


def _with_query_type(
    spec_dict: dict[str, Any],
    query_type: str,
) -> dict[str, Any]:
    mutated = dict(spec_dict)
    mutated["query_type"] = query_type
    if query_type == "shortest_path_cost":
        mutated["weighted"] = True
    return mutated


def _layer3_mutants(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    spec_dict: dict[str, Any],
    budget: int,
    seed: int,
    mode: str,
) -> list[Any]:
    candidates: list[Any] = []

    query_type = spec_dict.get("query_type")
    query_alternates = {
        "reachable": "min_hops",
        "min_hops": "shortest_path_cost",
        "shortest_path_cost": "reachable",
    }
    next_query = query_alternates.get(query_type)
    if next_query is not None:
        candidates.append(
            candidate(
                _with_query_type(spec_dict, next_query),
                mutant_kind="graph_queries_query_type_mutation",
                rule_id="graph_queries.query_type_swap",
                metadata={"path": ["query_type"], "to": next_query},
            )
        )

    for flag_name in ("directed", "weighted"):
        value = spec_dict.get(flag_name)
        if not isinstance(value, bool):
            continue
        flipped = set_at_path(spec_dict, (flag_name,), not value)
        if (
            flag_name == "weighted"
            and spec_dict.get("query_type") == "shortest_path_cost"
            and not flipped.get("weighted")
        ):
            continue
        candidates.append(
            candidate(
                flipped,
                mutant_kind="graph_queries_flag_mutation",
                rule_id=f"graph_queries.{flag_name}_flip",
                metadata={"path": [flag_name]},
            )
        )

    edges = spec_dict.get("edges")
    n_nodes = spec_dict.get("n_nodes")
    if isinstance(edges, list) and type(n_nodes) is int and n_nodes > 0:
        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                continue
            weight = edge.get("w")
            if type(weight) is int:
                for delta in (-1, 1):
                    updated = i64_add(weight, delta)
                    if updated is None or updated < 0:
                        continue
                    mutated_edge = dict(edge)
                    mutated_edge["w"] = updated
                    candidates.append(
                        candidate(
                            set_at_path(
                                spec_dict, ("edges", index), mutated_edge
                            ),
                            mutant_kind="graph_queries_edge_weight_mutation",
                            rule_id=(
                                "graph_queries.edge_weight_"
                                f"{'minus' if delta < 0 else 'plus'}_one"
                            ),
                            metadata={
                                "path": ["edges", index, "w"],
                                "delta": delta,
                            },
                        )
                    )

            u = edge.get("u")
            v = edge.get("v")
            if type(u) is int and type(v) is int and u != v:
                swapped = dict(edge)
                swapped["u"] = v
                swapped["v"] = u
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("edges", index), swapped),
                        mutant_kind="graph_queries_edge_endpoint_mutation",
                        rule_id="graph_queries.swap_edge_endpoints",
                        metadata={"path": ["edges", index], "swap": True},
                    )
                )

        if len(edges) > 1:
            for index in range(len(edges)):
                mutated_edges = list(edges)
                mutated_edges.pop(index)
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("edges",), mutated_edges),
                        mutant_kind="graph_queries_structural_mutation",
                        rule_id="graph_queries.remove_edge",
                        metadata={"path": ["edges"], "removed_index": index},
                    )
                )

    return finalize_candidates(
        candidates,
        validate_spec=lambda raw: validate_spec_for_family(FAMILY, raw),
        original_spec=spec_dict,
        task_id=task_id,
        family=FAMILY,
        seed=seed,
        mode=cast(Any, mode),
        budget=budget,
    )


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
    layer3_mutant_factory=_layer3_mutants,
)
