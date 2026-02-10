import random

from genfxn.core.sampling import pick_from_preferred
from genfxn.core.trace import TraceStep, trace_step
from genfxn.graph_queries.models import (
    GraphEdge,
    GraphQueriesAxes,
    GraphQueriesSpec,
    GraphQueryType,
)

_TARGET_QUERY_TYPE_PREFS: dict[int, list[GraphQueryType]] = {
    1: [GraphQueryType.REACHABLE],
    2: [GraphQueryType.MIN_HOPS, GraphQueryType.REACHABLE],
    3: [GraphQueryType.MIN_HOPS, GraphQueryType.SHORTEST_PATH_COST],
    4: [GraphQueryType.SHORTEST_PATH_COST, GraphQueryType.MIN_HOPS],
    5: [GraphQueryType.SHORTEST_PATH_COST],
}

_TARGET_DIRECTED_PREFS: dict[int, list[bool]] = {
    1: [False, True],
    2: [False, True],
    3: [True, False],
    4: [True, False],
    5: [True, False],
}

_TARGET_WEIGHTED_PREFS: dict[int, list[bool]] = {
    1: [False, True],
    2: [False, True],
    3: [True, False],
    4: [True, False],
    5: [True],
}

_TARGET_NODES_RANGES: dict[int, tuple[int, int]] = {
    1: (2, 4),
    2: (3, 6),
    3: (4, 8),
    4: (6, 10),
    5: (8, 12),
}

_TARGET_DENSITY_RANGES: dict[int, tuple[float, float]] = {
    1: (0.15, 0.35),
    2: (0.2, 0.4),
    3: (0.3, 0.55),
    4: (0.45, 0.75),
    5: (0.6, 0.9),
}


def _sample_probability(
    prob_range: tuple[float, float], rng: random.Random
) -> float:
    return rng.uniform(prob_range[0], prob_range[1])


def _sample_int_with_preferred_overlap(
    *,
    available: tuple[int, int],
    preferred: tuple[int, int],
    rng: random.Random,
) -> int:
    lo = max(available[0], preferred[0])
    hi = min(available[1], preferred[1])
    if lo <= hi:
        return rng.randint(lo, hi)
    return rng.randint(available[0], available[1])


def _max_unique_edges(n_nodes: int, directed: bool) -> int:
    if directed:
        return n_nodes * max(0, n_nodes - 1)
    return n_nodes * max(0, n_nodes - 1) // 2


def _preferred_edge_count_range(
    n_nodes: int,
    directed: bool,
    target_difficulty: int,
) -> tuple[int, int]:
    max_edges = max(1, _max_unique_edges(n_nodes, directed))
    density_lo, density_hi = _TARGET_DENSITY_RANGES[target_difficulty]
    lo = max(0, int(round(max_edges * density_lo)))
    hi = max(lo, int(round(max_edges * density_hi)))
    return (lo, hi)


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
        rng = random.Random()

    target_difficulty = axes.target_difficulty
    if target_difficulty is None:
        query_type = rng.choice(axes.query_types)
        directed = rng.choice(axes.directed_choices)
        weighted = rng.choice(axes.weighted_choices)
        n_nodes = rng.randint(axes.n_nodes_range[0], axes.n_nodes_range[1])
    else:
        query_type = pick_from_preferred(
            axes.query_types,
            _TARGET_QUERY_TYPE_PREFS[target_difficulty],
            rng,
        )
        directed = pick_from_preferred(
            axes.directed_choices,
            _TARGET_DIRECTED_PREFS[target_difficulty],
            rng,
        )
        weighted = pick_from_preferred(
            axes.weighted_choices,
            _TARGET_WEIGHTED_PREFS[target_difficulty],
            rng,
        )
        n_nodes = _sample_int_with_preferred_overlap(
            available=axes.n_nodes_range,
            preferred=_TARGET_NODES_RANGES[target_difficulty],
            rng=rng,
        )

    disconnected_prob = _sample_probability(axes.disconnected_prob_range, rng)
    multi_edge_prob = _sample_probability(axes.multi_edge_prob_range, rng)
    hub_bias_prob = _sample_probability(axes.hub_bias_prob_range, rng)

    if n_nodes <= 1:
        edge_count = 0
    elif target_difficulty is None:
        edge_count = rng.randint(
            axes.edge_count_range[0],
            axes.edge_count_range[1],
        )
    else:
        preferred_edges = _preferred_edge_count_range(
            n_nodes,
            directed,
            target_difficulty,
        )
        edge_count = _sample_int_with_preferred_overlap(
            available=axes.edge_count_range,
            preferred=preferred_edges,
            rng=rng,
        )

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
        if not candidates:
            break
        if seen_pairs and rng.random() < multi_edge_prob:
            u, v = rng.choice(seen_pairs)
        else:
            u, v = _pick_pair(candidates, hub, hub_bias_prob, rng)
        seen_pairs.append((u, v))
        weight = rng.randint(axes.weight_range[0], axes.weight_range[1])
        edges.append(GraphEdge(u=u, v=v, w=weight if weighted else 1))

    trace_step(
        trace,
        "sample_query_type",
        f"Query type: {query_type.value}",
        query_type.value,
    )
    trace_step(
        trace,
        "sample_directed",
        f"Directed: {directed}",
        directed,
    )
    trace_step(
        trace,
        "sample_weighted",
        f"Weighted: {weighted}",
        weighted,
    )
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
