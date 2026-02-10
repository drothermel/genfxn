import random
from collections import defaultdict
from collections.abc import Callable
from itertools import product
from typing import cast

import pytest

from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import QueryTag
from genfxn.graph_queries.eval import eval_graph_queries, normalize_graph
from genfxn.graph_queries.models import (
    GraphEdge,
    GraphQueriesAxes,
    GraphQueriesSpec,
    GraphQueryType,
)
from genfxn.graph_queries.queries import generate_graph_queries_queries
from genfxn.graph_queries.render import render_graph_queries
from genfxn.graph_queries.sampler import sample_graph_queries_spec
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.langs.types import Language


def _spec(query_type: GraphQueryType) -> GraphQueriesSpec:
    return GraphQueriesSpec(
        query_type=query_type,
        directed=True,
        weighted=True,
        n_nodes=4,
        edges=[
            GraphEdge(u=0, v=1, w=2),
            GraphEdge(u=1, v=2, w=3),
            GraphEdge(u=0, v=2, w=20),
        ],
    )


def _matrix_spec(
    query_type: GraphQueryType,
    *,
    directed: bool,
    weighted: bool,
) -> GraphQueriesSpec:
    return GraphQueriesSpec(
        query_type=query_type,
        directed=directed,
        weighted=weighted,
        n_nodes=6,
        edges=[
            GraphEdge(u=0, v=1, w=8),
            GraphEdge(u=0, v=1, w=2),
            GraphEdge(u=1, v=2, w=3),
            GraphEdge(u=2, v=3, w=1),
            GraphEdge(u=0, v=4, w=10),
        ],
    )


def test_eval_semantics_for_v1_query_types() -> None:
    reachable_spec = _spec(GraphQueryType.REACHABLE)
    assert eval_graph_queries(reachable_spec, 0, 2) == 1
    assert eval_graph_queries(reachable_spec, 2, 0) == 0
    assert eval_graph_queries(reachable_spec, 3, 3) == 1

    hops_spec = _spec(GraphQueryType.MIN_HOPS)
    assert eval_graph_queries(hops_spec, 0, 2) == 1
    assert eval_graph_queries(hops_spec, 2, 0) == -1
    assert eval_graph_queries(hops_spec, 3, 3) == 0

    cost_spec = _spec(GraphQueryType.SHORTEST_PATH_COST)
    assert eval_graph_queries(cost_spec, 0, 2) == 5
    assert eval_graph_queries(cost_spec, 2, 0) == -1
    assert eval_graph_queries(cost_spec, 3, 3) == 0


def test_shortest_path_cost_requires_weighted_true_in_spec() -> None:
    with pytest.raises(
        ValueError, match="shortest_path_cost requires weighted=True"
    ):
        GraphQueriesSpec(
            query_type=GraphQueryType.SHORTEST_PATH_COST,
            directed=True,
            weighted=False,
            n_nodes=3,
            edges=[GraphEdge(u=0, v=1, w=2)],
        )


def test_axes_reject_shortest_path_cost_without_weighted_true() -> None:
    with pytest.raises(
        ValueError, match="shortest_path_cost requires weighted=True"
    ):
        GraphQueriesAxes(
            query_types=[GraphQueryType.SHORTEST_PATH_COST],
            weighted_choices=[False],
        )


def test_normalize_graph_keeps_min_weight_for_duplicate_edges() -> None:
    spec = GraphQueriesSpec(
        query_type=GraphQueryType.SHORTEST_PATH_COST,
        directed=True,
        weighted=True,
        n_nodes=3,
        edges=[
            GraphEdge(u=0, v=1, w=10),
            GraphEdge(u=0, v=1, w=2),
            GraphEdge(u=1, v=2, w=5),
        ],
    )
    adjacency = normalize_graph(spec)
    assert adjacency == {
        0: [(1, 2)],
        1: [(2, 5)],
        2: [],
    }
    assert eval_graph_queries(spec, 0, 2) == 7


@pytest.mark.parametrize(
    ("query_type", "expected"),
    [
        (GraphQueryType.REACHABLE, 1),
        (GraphQueryType.MIN_HOPS, 2),
        (GraphQueryType.SHORTEST_PATH_COST, 9),
    ],
)
def test_eval_undirected_graph_is_symmetric(
    query_type: GraphQueryType,
    expected: int,
) -> None:
    spec = GraphQueriesSpec(
        query_type=query_type,
        directed=False,
        weighted=True,
        n_nodes=4,
        edges=[
            GraphEdge(u=0, v=1, w=4),
            GraphEdge(u=1, v=2, w=5),
        ],
    )
    assert eval_graph_queries(spec, 0, 2) == expected
    assert eval_graph_queries(spec, 2, 0) == expected


@pytest.mark.parametrize(
    ("src", "dst", "match"),
    [
        (-1, 0, "src=-1"),
        (4, 0, "src=4"),
        (0, -1, "dst=-1"),
        (0, 4, "dst=4"),
    ],
)
def test_eval_invalid_nodes_raise_value_error(
    src: int,
    dst: int,
    match: str,
) -> None:
    spec = _spec(GraphQueryType.REACHABLE)
    with pytest.raises(ValueError, match=match):
        eval_graph_queries(spec, src, dst)


@pytest.mark.parametrize(
    ("query_type", "directed", "weighted"),
    [
        (query_type, directed, weighted)
        for query_type, directed, weighted in product(
            GraphQueryType,
            (False, True),
            (False, True),
        )
        if not (
            query_type == GraphQueryType.SHORTEST_PATH_COST and not weighted
        )
    ],
    ids=[
        f"{query_type.value}-directed-{directed}-weighted-{weighted}"
        for query_type, directed, weighted in product(
            GraphQueryType,
            (False, True),
            (False, True),
        )
        if not (
            query_type == GraphQueryType.SHORTEST_PATH_COST and not weighted
        )
    ],
)
def test_rendered_python_matches_evaluator_across_v1_matrix(
    query_type: GraphQueryType,
    directed: bool,
    weighted: bool,
) -> None:
    spec = _matrix_spec(
        query_type,
        directed=directed,
        weighted=weighted,
    )
    code = render_graph_queries(spec)

    namespace: dict[str, object] = {}
    exec(code, namespace)  # noqa: S102
    rendered = cast(Callable[[int, int], int], namespace["f"])

    inputs = [(0, 2), (2, 0), (0, 4), (4, 0), (5, 0), (5, 5)]
    for src, dst in inputs:
        assert rendered(src, dst) == eval_graph_queries(spec, src, dst)


def test_sampler_is_deterministic_for_seed() -> None:
    axes = GraphQueriesAxes(
        target_difficulty=3,
        query_types=[GraphQueryType.MIN_HOPS],
        directed_choices=[True],
        weighted_choices=[True],
        n_nodes_range=(5, 5),
        edge_count_range=(7, 7),
        weight_range=(2, 2),
        disconnected_prob_range=(0.0, 0.0),
        multi_edge_prob_range=(0.0, 0.0),
        hub_bias_prob_range=(0.0, 0.0),
    )
    spec1 = sample_graph_queries_spec(axes, random.Random(42))
    spec2 = sample_graph_queries_spec(axes, random.Random(42))
    assert spec1.model_dump() == spec2.model_dump()


def _compute_graph_queries_difficulty(spec: GraphQueriesSpec) -> int:
    try:
        return compute_difficulty("graph_queries", spec.model_dump())
    except ValueError as exc:
        if "Unknown family: graph_queries" in str(exc):
            pytest.skip(
                "compute_difficulty('graph_queries', ...) is not available"
            )
        raise


def test_queries_cover_all_tags_and_match_eval_across_multiple_seeds() -> None:
    axes = GraphQueriesAxes(
        query_types=list(GraphQueryType),
        directed_choices=[False, True],
        weighted_choices=[False, True],
        n_nodes_range=(2, 9),
        edge_count_range=(1, 24),
        weight_range=(1, 9),
        disconnected_prob_range=(0.0, 0.5),
        multi_edge_prob_range=(0.0, 0.3),
        hub_bias_prob_range=(0.0, 0.5),
    )

    for seed in range(220, 236):
        spec = sample_graph_queries_spec(axes, random.Random(seed))
        queries = generate_graph_queries_queries(
            spec,
            axes,
            random.Random(seed),
        )
        assert queries
        assert {query.tag for query in queries} == set(QueryTag)
        for query in queries:
            assert query.output == eval_graph_queries(
                spec,
                query.input["src"],
                query.input["dst"],
            )


def test_query_input_uniqueness_contract_is_per_tag() -> None:
    spec = GraphQueriesSpec(
        query_type=GraphQueryType.REACHABLE,
        directed=False,
        weighted=False,
        n_nodes=1,
        edges=[],
    )
    axes = GraphQueriesAxes(
        query_types=[GraphQueryType.REACHABLE],
        directed_choices=[False],
        weighted_choices=[False],
        n_nodes_range=(1, 1),
        edge_count_range=(0, 0),
        weight_range=(1, 1),
        disconnected_prob_range=(0.0, 0.0),
        multi_edge_prob_range=(0.0, 0.0),
        hub_bias_prob_range=(0.0, 0.0),
    )
    queries = generate_graph_queries_queries(spec, axes, random.Random(0))

    seen_by_tag: dict[QueryTag, set[tuple[int, int]]] = {
        tag: set() for tag in QueryTag
    }
    tags_by_pair: dict[tuple[int, int], set[QueryTag]] = defaultdict(set)
    for query in queries:
        pair = (query.input["src"], query.input["dst"])
        assert pair not in seen_by_tag[query.tag]
        seen_by_tag[query.tag].add(pair)
        tags_by_pair[pair].add(query.tag)

    assert len(tags_by_pair) == 1
    assert any(len(tags) > 1 for tags in tags_by_pair.values())


def test_queries_inputs_stay_within_node_bounds_across_multiple_seeds() -> None:
    axes = GraphQueriesAxes(
        query_types=list(GraphQueryType),
        directed_choices=[False, True],
        weighted_choices=[False, True],
        n_nodes_range=(1, 10),
        edge_count_range=(0, 30),
        weight_range=(1, 12),
        disconnected_prob_range=(0.0, 0.8),
        multi_edge_prob_range=(0.0, 0.6),
        hub_bias_prob_range=(0.0, 0.8),
    )

    for seed in range(320, 352):
        spec = sample_graph_queries_spec(axes, random.Random(seed))
        queries = generate_graph_queries_queries(
            spec,
            axes,
            random.Random(seed),
        )
        assert queries
        for query in queries:
            src = query.input["src"]
            dst = query.input["dst"]
            assert 0 <= src < spec.n_nodes
            assert 0 <= dst < spec.n_nodes


def test_sampler_respects_target_difficulty_axis_when_available() -> None:
    samples_per_target = 120

    def _sample_difficulty_average(target: int) -> float:
        axes = GraphQueriesAxes(target_difficulty=target)
        rng = random.Random(8100 + target)
        scores = []
        for _ in range(samples_per_target):
            spec = sample_graph_queries_spec(axes, rng)
            scores.append(_compute_graph_queries_difficulty(spec))
        return sum(scores) / len(scores)

    averages = {
        target: _sample_difficulty_average(target) for target in range(1, 6)
    }

    for target in range(1, 5):
        assert averages[target + 1] >= averages[target] - 0.05
    assert averages[5] >= averages[1] + 0.7


def test_generate_task_deterministic_and_consistent() -> None:
    axes = GraphQueriesAxes(
        target_difficulty=2,
        query_types=[GraphQueryType.REACHABLE],
        directed_choices=[False],
        weighted_choices=[False],
        n_nodes_range=(4, 4),
        edge_count_range=(3, 3),
        weight_range=(1, 1),
        disconnected_prob_range=(0.0, 0.0),
        multi_edge_prob_range=(0.0, 0.0),
        hub_bias_prob_range=(0.0, 0.0),
    )

    task1 = generate_graph_queries_task(axes=axes, rng=random.Random(123))
    task2 = generate_graph_queries_task(axes=axes, rng=random.Random(123))

    assert task1.family == "graph_queries"
    assert task1.task_id == task2.task_id
    assert task1.spec == task2.spec
    assert task1.queries == task2.queries
    assert task1.description
    assert set(query.tag for query in task1.queries) == set(QueryTag)

    spec = GraphQueriesSpec.model_validate(task1.spec)
    for query in task1.queries:
        assert query.output == eval_graph_queries(
            spec,
            query.input["src"],
            query.input["dst"],
        )


def test_m0_language_behavior() -> None:
    task = generate_graph_queries_task(
        rng=random.Random(7),
        languages=[Language.PYTHON],
    )
    assert isinstance(task.code, dict)
    assert set(task.code) == {Language.PYTHON.value}
