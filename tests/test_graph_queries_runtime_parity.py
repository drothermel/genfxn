import random
import tempfile
from pathlib import Path
from typing import Any

import pytest
from helpers import (
    require_java_runtime,
    require_rust_runtime,
    run_checked_subprocess,
)

from genfxn.graph_queries.eval import eval_graph_queries
from genfxn.graph_queries.models import (
    GraphEdge,
    GraphQueriesAxes,
    GraphQueriesSpec,
    GraphQueryType,
)
from genfxn.graph_queries.sampler import sample_graph_queries_spec
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language


def _parse_query_input(input_value: Any) -> tuple[int, int]:
    if not isinstance(input_value, dict):
        raise TypeError("graph_queries query input must be a dict")

    src = input_value.get("src")
    dst = input_value.get("dst")
    if not isinstance(src, int) or not isinstance(dst, int):
        raise TypeError(
            "graph_queries query input must contain integer src/dst"
        )
    return src, dst


def _run_java_f(
    javac: str,
    java: str,
    code: str,
    src: int,
    dst: int,
) -> int:
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    System.out.print(f({src}, {dst}));\n"
        "  }\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src_path = tmp / "Main.java"
        src_path.write_text(main_src, encoding="utf-8")
        run_checked_subprocess(
            [javac, str(src_path)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [java, "-cp", str(tmp), "Main"],
            cwd=tmp,
        )
        return int(proc.stdout.strip())


def _run_rust_f(
    rustc: str,
    code: str,
    src: int,
    dst: int,
) -> int:
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    println!(\"{{}}\", f({src}, {dst}));\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src_path = tmp / "main.rs"
        out = tmp / "main_bin"
        src_path.write_text(main_src, encoding="utf-8")
        run_checked_subprocess(
            [rustc, str(src_path), "-O", "-o", str(out)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [str(out)],
            cwd=tmp,
        )
        return int(proc.stdout.strip())


def _sample_pairs(n_nodes: int) -> tuple[tuple[int, int], ...]:
    last = n_nodes - 1
    mid = n_nodes // 2
    candidates = [
        (0, 0),
        (0, last),
        (last, 0),
        (last, last),
        (mid, last),
        (last, mid),
    ]

    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for pair in candidates:
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
    return tuple(pairs)


@pytest.mark.full
def test_graph_queries_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_graph_queries_task(rng=random.Random(42))
    spec = GraphQueriesSpec.model_validate(task.spec)
    java_code = get_render_fn(Language.JAVA, "graph_queries")(
        spec,
        func_name="f",
    )

    for query in task.queries:
        src, dst = _parse_query_input(query.input)
        expected = eval_graph_queries(spec, src, dst)
        actual = _run_java_f(javac, java, java_code, src, dst)
        assert actual == expected


@pytest.mark.full
def test_graph_queries_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_graph_queries_task(rng=random.Random(99))
    spec = GraphQueriesSpec.model_validate(task.spec)
    rust_code = get_render_fn(Language.RUST, "graph_queries")(
        spec,
        func_name="f",
    )

    for query in task.queries:
        src, dst = _parse_query_input(query.input)
        expected = eval_graph_queries(spec, src, dst)
        actual = _run_rust_f(rustc, rust_code, src, dst)
        assert actual == expected


@pytest.mark.full
def test_graph_queries_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    render_graph_queries_java = get_render_fn(Language.JAVA, "graph_queries")
    render_graph_queries_rust = get_render_fn(Language.RUST, "graph_queries")

    rng = random.Random(77)
    for _ in range(8):
        spec = sample_graph_queries_spec(GraphQueriesAxes(), rng=rng)
        java_code = render_graph_queries_java(spec, func_name="f")
        rust_code = render_graph_queries_rust(spec, func_name="f")

        for src, dst in _sample_pairs(spec.n_nodes):
            expected = eval_graph_queries(spec, src, dst)
            assert _run_java_f(javac, java, java_code, src, dst) == expected
            assert _run_rust_f(rustc, rust_code, src, dst) == expected


@pytest.mark.full
def test_graph_queries_runtime_parity_forced_query_types() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    render_graph_queries_java = get_render_fn(Language.JAVA, "graph_queries")
    render_graph_queries_rust = get_render_fn(Language.RUST, "graph_queries")

    base_edges = [
        GraphEdge(u=0, v=1, w=2),
        GraphEdge(u=1, v=2, w=3),
        GraphEdge(u=0, v=2, w=10),
    ]
    specs: tuple[GraphQueriesSpec, ...] = (
        GraphQueriesSpec(
            query_type=GraphQueryType.REACHABLE,
            directed=False,
            weighted=False,
            n_nodes=3,
            edges=base_edges,
        ),
        GraphQueriesSpec(
            query_type=GraphQueryType.MIN_HOPS,
            directed=True,
            weighted=False,
            n_nodes=3,
            edges=base_edges,
        ),
        GraphQueriesSpec(
            query_type=GraphQueryType.SHORTEST_PATH_COST,
            directed=True,
            weighted=True,
            n_nodes=3,
            edges=base_edges,
        ),
    )
    pairs = ((0, 2), (2, 0), (1, 1))

    for spec in specs:
        java_code = render_graph_queries_java(spec, func_name="f")
        rust_code = render_graph_queries_rust(spec, func_name="f")
        for src, dst in pairs:
            expected = eval_graph_queries(spec, src, dst)
            assert _run_java_f(javac, java, java_code, src, dst) == expected
            assert _run_rust_f(rustc, rust_code, src, dst) == expected


@pytest.mark.full
def test_graph_queries_runtime_parity_large_weight_cost_accumulation() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    render_graph_queries_java = get_render_fn(Language.JAVA, "graph_queries")
    render_graph_queries_rust = get_render_fn(Language.RUST, "graph_queries")

    spec = GraphQueriesSpec(
        query_type=GraphQueryType.SHORTEST_PATH_COST,
        directed=True,
        weighted=True,
        n_nodes=3,
        edges=[
            GraphEdge(u=0, v=1, w=2_000_000_000),
            GraphEdge(u=1, v=2, w=2_000_000_000),
        ],
    )
    java_code = render_graph_queries_java(spec, func_name="f")
    rust_code = render_graph_queries_rust(spec, func_name="f")

    expected = eval_graph_queries(spec, 0, 2)
    assert expected == 4_000_000_000
    assert _run_java_f(javac, java, java_code, 0, 2) == expected
    assert _run_rust_f(rustc, rust_code, 0, 2) == expected
