import random

from genfxn.core.sampling import sample_probability
from genfxn.core.trace import TraceStep, trace_step
from genfxn.graph_queries.models import (
    GraphEdge,
    GraphQueriesAxes,
    GraphQueriesSpec,
    GraphQueryType,
)


def _max_unique_edges(n_nodes: int, directed: bool) -> int:
    if directed:
        return n_nodes * max(0, n_nodes - 1)
    return n_nodes * max(0, n_nodes - 1) // 2


def _candidate_pairs(
    n_nodes: int,
    directed: bool,
    disconnected: bool,
    rng: random.Random,
) -> list[tuple[int, int]]:
    if n_nodes <= 1:
        return []

    side_by_node: dict[int, int] = {}
    if disconnected and n_nodes >= 4:
        nodes = list(range(n_nodes))
        rng.shuffle(nodes)
        cut = rng.randint(1, n_nodes - 1)
        for node in nodes[:cut]:
            side_by_node[node] = 0
        for node in nodes[cut:]:
            side_by_node[node] = 1

    pairs: list[tuple[int, int]] = []
    for u in range(n_nodes):
        for v in range(n_nodes):
            if u == v:
                continue
            if not directed and u > v:
                continue
            if side_by_node and side_by_node.get(u) != side_by_node.get(v):
                continue
            pairs.append((u, v))
    return pairs


def _pick_pair(
    candidates: list[tuple[int, int]],
    hub: int | None,
    hub_bias_prob: float,
    rng: random.Random,
) -> tuple[int, int]:
    if hub is not None and rng.random() < hub_bias_prob:
        hub_candidates = [pair for pair in candidates if hub in pair]
        if hub_candidates:
            return rng.choice(hub_candidates)
    return rng.choice(candidates)


def sample_graph_queries_spec(
    axes: GraphQueriesAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> GraphQueriesSpec:
    if rng is None:
        rng = random.Random()  # noqa: S311

    query_type = rng.choice(axes.query_types)
    directed = rng.choice(axes.directed_choices)
    if query_type == GraphQueryType.SHORTEST_PATH_COST:
        weighted_candidates = [
            value for value in axes.weighted_choices if value
        ]
        if not weighted_candidates:
            raise ValueError("shortest_path_cost requires weighted=True")
        weighted = rng.choice(weighted_candidates)
    else:
        weighted = rng.choice(axes.weighted_choices)
    n_nodes = rng.randint(axes.n_nodes_range[0], axes.n_nodes_range[1])

    disconnected_prob = sample_probability(axes.disconnected_prob_range, rng)
    multi_edge_prob = sample_probability(axes.multi_edge_prob_range, rng)
    hub_bias_prob = sample_probability(axes.hub_bias_prob_range, rng)

    max_edges = _max_unique_edges(n_nodes, directed)
    edge_count_hi = min(axes.edge_count_range[1], max_edges)
    edge_count_lo = min(axes.edge_count_range[0], edge_count_hi)
    edge_count = rng.randint(edge_count_lo, edge_count_hi)

    disconnected = n_nodes >= 4 and rng.random() < disconnected_prob
    candidates = _candidate_pairs(
        n_nodes=n_nodes,
        directed=directed,
        disconnected=disconnected,
        rng=rng,
    )

    hub = None
    if n_nodes > 1 and rng.random() < hub_bias_prob:
        hub = rng.randrange(n_nodes)

    edges: list[GraphEdge] = []
    seen_pairs: list[tuple[int, int]] = []
    for _ in range(edge_count):
        use_multi_edge = (
            multi_edge_prob > 0.0
            and bool(seen_pairs)
            and (not candidates or rng.random() < multi_edge_prob)
        )
        if use_multi_edge:
            u, v = rng.choice(seen_pairs)
        elif candidates:
            u, v = _pick_pair(candidates, hub, hub_bias_prob, rng)
            candidates.remove((u, v))
        else:
            break
        seen_pairs.append((u, v))
        weight = rng.randint(axes.weight_range[0], axes.weight_range[1])
        edges.append(GraphEdge(u=u, v=v, w=weight))

    trace_step(
        trace,
        "sample_query_type",
        f"Query type: {query_type.value}",
        query_type.value,
    )
    trace_step(trace, "sample_directed", f"Directed: {directed}", directed)
    trace_step(trace, "sample_weighted", f"Weighted: {weighted}", weighted)
    trace_step(trace, "sample_n_nodes", f"Node count: {n_nodes}", n_nodes)
    trace_step(
        trace,
        "sample_edge_count",
        f"Edge count: {len(edges)}",
        len(edges),
    )
    trace_step(
        trace,
        "sample_disconnected_prob",
        "Disconnected probability sampled for edge construction",
        disconnected_prob,
    )
    trace_step(
        trace,
        "sample_multi_edge_prob",
        "Multi-edge probability sampled for edge construction",
        multi_edge_prob,
    )
    trace_step(
        trace,
        "sample_hub_bias_prob",
        "Hub bias probability sampled for edge construction",
        hub_bias_prob,
    )

    return GraphQueriesSpec(
        query_type=query_type,
        directed=directed,
        weighted=weighted,
        n_nodes=n_nodes,
        edges=edges,
    )
