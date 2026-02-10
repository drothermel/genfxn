import random

from genfxn.core.trace import TraceStep, trace_step
from genfxn.graph_queries.models import (
    GraphEdge,
    GraphQueriesAxes,
    GraphQueriesSpec,
    GraphQueryType,
)

_TARGET_QUERY_TYPE_PREFS: dict[int, list[GraphQueryType]] = {
    1: [GraphQueryType.REACHABLE],
    2: [GraphQueryType.REACHABLE, GraphQueryType.MIN_HOPS],
    3: [GraphQueryType.MIN_HOPS, GraphQueryType.SHORTEST_PATH_COST],
    4: [GraphQueryType.SHORTEST_PATH_COST, GraphQueryType.MIN_HOPS],
    5: [GraphQueryType.SHORTEST_PATH_COST],
}

_TARGET_DIRECTED_PREFS: dict[int, list[bool]] = {
    1: [False],
    2: [False, True],
    3: [True, False],
    4: [True],
    5: [True],
}

_TARGET_WEIGHTED_PREFS: dict[int, list[bool]] = {
    1: [False],
    2: [False, True],
    3: [True, False],
    4: [True],
    5: [True],
}

_TARGET_NODES_RANGES: dict[int, tuple[int, int]] = {
    1: (2, 3),
    2: (3, 5),
    3: (5, 7),
    4: (7, 10),
    5: (9, 12),
}

_TARGET_DENSITY_RANGES: dict[int, tuple[float, float]] = {
    1: (0.1, 0.22),
    2: (0.18, 0.34),
    3: (0.3, 0.5),
    4: (0.45, 0.68),
    5: (0.62, 0.88),
}


def _sample_probability(
    prob_range: tuple[float, float], rng: random.Random
) -> float:
    return rng.uniform(prob_range[0], prob_range[1])


def _sample_probability_for_target(
    prob_range: tuple[float, float],
    target_difficulty: int,
    rng: random.Random,
    *,
    invert: bool = False,
) -> float:
    lo, hi = prob_range
    if lo == hi:
        return lo
    level = (target_difficulty - 1) / 4
    if invert:
        level = 1.0 - level
    span = hi - lo
    center = lo + span * level
    jitter = min(span * 0.08, span / 2)
    sampled = rng.uniform(center - jitter, center + jitter)
    return min(max(sampled, lo), hi)


def _pick_from_ranked_preference[T](
    available: list[T],
    preferred: list[T],
    rng: random.Random,
) -> T:
    preferred_available = [item for item in preferred if item in available]
    if not preferred_available:
        return rng.choice(available)
    weights = [
        1 << (len(preferred_available) - index - 1)
        for index in range(len(preferred_available))
    ]
    total = sum(weights)
    draw = rng.randrange(total)
    for item, weight in zip(preferred_available, weights, strict=True):
        if draw < weight:
            return item
        draw -= weight
    return preferred_available[-1]


def _sample_int_with_preferred_overlap(
    *,
    available: tuple[int, int],
    preferred: tuple[int, int],
    rng: random.Random,
) -> int:
    available_lo, available_hi = available
    preferred_lo, preferred_hi = preferred
    lo = max(available_lo, preferred_lo)
    hi = min(available_hi, preferred_hi)
    if lo <= hi:
        return rng.randint(lo, hi)

    span = max(1, available_hi - available_lo + 1)
    band = max(1, span // 4)
    if available_hi < preferred_lo:
        band_lo = max(available_lo, available_hi - band + 1)
        return rng.randint(band_lo, available_hi)
    if available_lo > preferred_hi:
        band_hi = min(available_hi, available_lo + band - 1)
        return rng.randint(available_lo, band_hi)
    return rng.randint(available_lo, available_hi)


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
        rng = random.Random()  # noqa: S311

    target_difficulty = axes.target_difficulty
    if target_difficulty is None:
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
    else:
        query_type = _pick_from_ranked_preference(
            axes.query_types,
            _TARGET_QUERY_TYPE_PREFS[target_difficulty],
            rng,
        )
        directed = _pick_from_ranked_preference(
            axes.directed_choices,
            _TARGET_DIRECTED_PREFS[target_difficulty],
            rng,
        )
        if query_type == GraphQueryType.SHORTEST_PATH_COST:
            weighted_candidates = [
                value for value in axes.weighted_choices if value
            ]
            if not weighted_candidates:
                raise ValueError("shortest_path_cost requires weighted=True")
            weighted = _pick_from_ranked_preference(
                weighted_candidates,
                [True],
                rng,
            )
        else:
            weighted = _pick_from_ranked_preference(
                axes.weighted_choices,
                _TARGET_WEIGHTED_PREFS[target_difficulty],
                rng,
            )
        n_nodes = _sample_int_with_preferred_overlap(
            available=axes.n_nodes_range,
            preferred=_TARGET_NODES_RANGES[target_difficulty],
            rng=rng,
        )

    if target_difficulty is None:
        disconnected_prob = _sample_probability(
            axes.disconnected_prob_range, rng
        )
        multi_edge_prob = _sample_probability(axes.multi_edge_prob_range, rng)
        hub_bias_prob = _sample_probability(axes.hub_bias_prob_range, rng)
    else:
        disconnected_prob = _sample_probability_for_target(
            axes.disconnected_prob_range,
            target_difficulty,
            rng,
            invert=True,
        )
        multi_edge_prob = _sample_probability_for_target(
            axes.multi_edge_prob_range,
            target_difficulty,
            rng,
        )
        hub_bias_prob = _sample_probability_for_target(
            axes.hub_bias_prob_range,
            target_difficulty,
            rng,
            invert=True,
        )

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
