import random

from genfxn.core.models import Query, QueryTag
from genfxn.graph_queries.eval import eval_graph_queries, normalize_graph
from genfxn.graph_queries.models import (
    GraphQueriesAxes,
    GraphQueriesSpec,
    GraphQueryType,
)


def _query_input(src: int, dst: int) -> dict[str, int]:
    return {"src": src, "dst": dst}


def _unreachable_output(query_type: GraphQueryType) -> int:
    if query_type == GraphQueryType.REACHABLE:
        return 0
    return -1


def generate_graph_queries_queries(
    spec: GraphQueriesSpec,
    axes: GraphQueriesAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    del axes  # M0: keep signature consistent with other families.
    n_nodes = spec.n_nodes
    adjacency = normalize_graph(spec)
    queries: list[Query] = []
    seen: set[tuple[QueryTag, int, int]] = set()

    def _append_query(src: int, dst: int, tag: QueryTag) -> None:
        key = (tag, src, dst)
        if key in seen:
            return
        seen.add(key)
        queries.append(
            Query(
                input=_query_input(src, dst),
                output=eval_graph_queries(spec, src, dst),
                tag=tag,
            )
        )

    _append_query(0, 0, QueryTag.COVERAGE)
    if n_nodes > 1:
        _append_query(0, 1, QueryTag.COVERAGE)
        _append_query(1, 0, QueryTag.COVERAGE)

    direct_pair: tuple[int, int] | None = None
    for src, neighbors in adjacency.items():
        if not neighbors:
            continue
        direct_pair = (src, neighbors[0][0])
        break
    if direct_pair is not None:
        _append_query(direct_pair[0], direct_pair[1], QueryTag.COVERAGE)

    unreachable_value = _unreachable_output(spec.query_type)
    found_unreachable = False
    for src in range(n_nodes):
        for dst in range(n_nodes):
            if src == dst:
                continue
            result = eval_graph_queries(spec, src, dst)
            if result != unreachable_value:
                continue
            _append_query(src, dst, QueryTag.COVERAGE)
            found_unreachable = True
            break
        if found_unreachable:
            break

    _append_query(n_nodes - 1, n_nodes - 1, QueryTag.BOUNDARY)
    if n_nodes > 1:
        _append_query(0, n_nodes - 1, QueryTag.BOUNDARY)
        _append_query(n_nodes - 1, 0, QueryTag.BOUNDARY)

    typical_count = min(max(3, n_nodes), 6)
    for _ in range(typical_count):
        src = rng.randrange(n_nodes)
        dst = rng.randrange(n_nodes)
        _append_query(src, dst, QueryTag.TYPICAL)

    if n_nodes > 1:
        degree_by_node = {
            node: len(neighbors) for node, neighbors in adjacency.items()
        }
        hub = max(degree_by_node, key=lambda node: degree_by_node[node])
        leaf = min(degree_by_node, key=lambda node: degree_by_node[node])
        _append_query(hub, leaf, QueryTag.ADVERSARIAL)
        _append_query(leaf, hub, QueryTag.ADVERSARIAL)
    _append_query(0, 0, QueryTag.ADVERSARIAL)

    for tag in QueryTag:
        if any(query.tag == tag for query in queries):
            continue
        shift = list(QueryTag).index(tag)
        src = min(shift, n_nodes - 1)
        dst = n_nodes - 1 - src
        _append_query(src, dst, tag)

    return queries
