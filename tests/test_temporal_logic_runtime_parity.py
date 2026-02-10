import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from helpers import require_java_runtime, require_rust_runtime

from genfxn.langs.java.temporal_logic import _long_literal
from genfxn.langs.registry import get_render_fn
from genfxn.langs.rust.temporal_logic import _i64_literal
from genfxn.langs.types import Language
from genfxn.temporal_logic.eval import eval_temporal_logic
from genfxn.temporal_logic.models import (
    TemporalLogicAxes,
    TemporalLogicSpec,
    TemporalOutputMode,
)
from genfxn.temporal_logic.sampler import sample_temporal_logic_spec
from genfxn.temporal_logic.task import generate_temporal_logic_task


def _parse_query_input(input_value: Any) -> list[int]:
    if not isinstance(input_value, list):
        raise TypeError("temporal_logic query input must be list[int]")
    if not all(isinstance(v, int) for v in input_value):
        raise TypeError("temporal_logic query input must be list[int]")
    return [int(v) for v in input_value]


def _run_java_f(
    javac: str,
    java: str,
    code: str,
    xs: list[int],
) -> int:
    xs_lit = ", ".join(_long_literal(v) for v in xs)
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    long[] xs = new long[]{{{xs_lit}}};\n"
        "    System.out.print(f(xs));\n"
        "  }\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src = tmp / "Main.java"
        src.write_text(main_src, encoding="utf-8")
        subprocess.run(  # noqa: S603
            [javac, str(src)],
            check=True,
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        proc = subprocess.run(  # noqa: S603
            [java, "-cp", str(tmp), "Main"],
            check=True,
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        return int(proc.stdout.strip())


def _run_rust_f(rustc: str, code: str, xs: list[int]) -> int:
    xs_lit = ", ".join(_i64_literal(v) for v in xs)
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
        "    println!(\"{}\", f(&xs));\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src = tmp / "main.rs"
        out = tmp / "main_bin"
        src.write_text(main_src, encoding="utf-8")
        subprocess.run(  # noqa: S603
            [rustc, str(src), "-O", "-o", str(out)],
            check=True,
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        proc = subprocess.run(  # noqa: S603
            [str(out)],
            check=True,
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        return int(proc.stdout.strip())


@pytest.mark.full
def test_temporal_logic_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_temporal_logic_task(rng=random.Random(42))
    spec = TemporalLogicSpec.model_validate(task.spec)
    java_code = get_render_fn(Language.JAVA, "temporal_logic")(
        spec,
        func_name="f",
    )

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_temporal_logic(spec, xs)
        actual = _run_java_f(javac, java, java_code, xs)
        assert actual == expected


@pytest.mark.full
def test_temporal_logic_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_temporal_logic_task(rng=random.Random(99))
    spec = TemporalLogicSpec.model_validate(task.spec)
    rust_code = get_render_fn(Language.RUST, "temporal_logic")(
        spec,
        func_name="f",
    )

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_temporal_logic(spec, xs)
        actual = _run_rust_f(rustc, rust_code, xs)
        assert actual == expected


@pytest.mark.full
def test_temporal_logic_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    render_java = get_render_fn(Language.JAVA, "temporal_logic")
    render_rust = get_render_fn(Language.RUST, "temporal_logic")

    sample_inputs = (
        [],
        [0],
        [1, -1],
        [-2, -1, 0, 1, 2],
        [5, 5, 5, 5],
        [3, 0, -3, 0, 3],
        [7, -8, 9, -10, 11, -12],
    )
    rng = random.Random(77)
    axes = TemporalLogicAxes(
        formula_depth_range=(1, 5),
        sequence_length_range=(0, 9),
        value_range=(-10, 10),
        predicate_constant_range=(-9, 9),
    )
    for _ in range(8):
        spec = sample_temporal_logic_spec(axes, rng=rng)
        java_code = render_java(spec, func_name="f")
        rust_code = render_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_temporal_logic(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected


@pytest.mark.full
def test_temporal_logic_runtime_parity_forced_output_modes() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    render_java = get_render_fn(Language.JAVA, "temporal_logic")
    render_rust = get_render_fn(Language.RUST, "temporal_logic")

    formula = {"op": "atom", "predicate": "gt", "constant": 0}
    sample_inputs = ([1, -1, 2], [-5, -4, -3], [0, 1, 0, 1])
    for output_mode in TemporalOutputMode:
        spec = TemporalLogicSpec(output_mode=output_mode, formula=formula)
        java_code = render_java(spec, func_name="f")
        rust_code = render_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_temporal_logic(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected
