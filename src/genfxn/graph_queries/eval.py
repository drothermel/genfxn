import heapq
from collections import deque

from genfxn.graph_queries.models import GraphQueriesSpec, GraphQueryType

Adjacency = dict[int, list[tuple[int, int]]]


def _validate_node(node: int, n_nodes: int, name: str) -> None:
    if type(node) is not int:
        raise ValueError(f"{name} must be int, got {type(node).__name__}")
    if node < 0 or node >= n_nodes:
        raise ValueError(f"{name}={node} must be in [0, {n_nodes - 1}]")


def _validate_spec_for_eval(spec: GraphQueriesSpec) -> None:
    if spec.n_nodes < 1:
        raise ValueError("n_nodes must be >= 1")
    for index, edge in enumerate(spec.edges):
        _validate_node(edge.u, spec.n_nodes, f"edges[{index}].u")
        _validate_node(edge.v, spec.n_nodes, f"edges[{index}].v")
        if edge.w < 0:
            raise ValueError(f"edges[{index}].w={edge.w} must be >= 0")


def _build_normalized_adjacency(spec: GraphQueriesSpec) -> Adjacency:
    best_weight_by_edge: dict[tuple[int, int], int] = {}
    for edge in spec.edges:
        weight = edge.w if spec.weighted else 1
        key = (edge.u, edge.v)
        prior = best_weight_by_edge.get(key)
        if prior is None or weight < prior:
            best_weight_by_edge[key] = weight

        if spec.directed:
            continue

        rev_key = (edge.v, edge.u)
        rev_prior = best_weight_by_edge.get(rev_key)
        if rev_prior is None or weight < rev_prior:
            best_weight_by_edge[rev_key] = weight

    adjacency: Adjacency = {node: [] for node in range(spec.n_nodes)}
    for (u, v), weight in best_weight_by_edge.items():
        adjacency[u].append((v, weight))
    for neighbors in adjacency.values():
        neighbors.sort(key=lambda item: (item[0], item[1]))
    return adjacency


def normalize_graph(spec: GraphQueriesSpec) -> Adjacency:
    _validate_spec_for_eval(spec)
    return _build_normalized_adjacency(spec)


def _is_reachable(adjacency: Adjacency, src: int, dst: int) -> bool:
    visited = {src}
    queue: deque[int] = deque([src])

    while queue:
        node = queue.popleft()
        if node == dst:
            return True
        for neighbor, _ in adjacency[node]:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append(neighbor)

    return False


def _min_hops(adjacency: Adjacency, src: int, dst: int) -> int:
    visited = {src}
    queue: deque[tuple[int, int]] = deque([(src, 0)])

    while queue:
        node, hops = queue.popleft()
        if node == dst:
            return hops
        for neighbor, _ in adjacency[node]:
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, hops + 1))

    return -1


def _shortest_path_cost(adjacency: Adjacency, src: int, dst: int) -> int:
    best_cost: dict[int, int] = {src: 0}
    heap: list[tuple[int, int]] = [(0, src)]

    while heap:
        cost, node = heapq.heappop(heap)
        if cost > best_cost.get(node, cost):
            continue
        if node == dst:
            return cost
        for neighbor, weight in adjacency[node]:
            next_cost = cost + weight
            prior = best_cost.get(neighbor)
            if prior is not None and next_cost >= prior:
                continue
            best_cost[neighbor] = next_cost
            heapq.heappush(heap, (next_cost, neighbor))

    return -1


def eval_graph_queries(spec: GraphQueriesSpec, src: int, dst: int) -> int:
    _validate_spec_for_eval(spec)
    _validate_node(src, spec.n_nodes, "src")
    _validate_node(dst, spec.n_nodes, "dst")

    if src == dst:
        if spec.query_type == GraphQueryType.REACHABLE:
            return 1
        return 0

    adjacency = _build_normalized_adjacency(spec)
    if spec.query_type == GraphQueryType.REACHABLE:
        return 1 if _is_reachable(adjacency, src, dst) else 0
    if spec.query_type == GraphQueryType.MIN_HOPS:
        return _min_hops(adjacency, src, dst)
    if spec.query_type == GraphQueryType.SHORTEST_PATH_COST:
        return _shortest_path_cost(adjacency, src, dst)

    raise ValueError(f"Unsupported query_type: {spec.query_type}")
