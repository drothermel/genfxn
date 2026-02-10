import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from helpers import require_java_runtime, require_rust_runtime

from genfxn.intervals.eval import eval_intervals
from genfxn.intervals.models import IntervalsAxes, IntervalsSpec
from genfxn.intervals.sampler import sample_intervals_spec
from genfxn.intervals.task import generate_intervals_task
from genfxn.langs.java.intervals import (
    render_intervals as render_intervals_java,
)
from genfxn.langs.rust.intervals import (
    render_intervals as render_intervals_rust,
)


def _long_literal(value: int) -> str:
    if value == -(1 << 63):
        return "Long.MIN_VALUE"
    return f"{value}L"


def _i64_literal(value: int) -> str:
    if value == -(1 << 63):
        return "i64::MIN"
    return f"{value}i64"


def _parse_query_input(input_value: Any) -> list[tuple[int, int]]:
    if not isinstance(input_value, list):
        raise TypeError("intervals query input must be a list")

    parsed: list[tuple[int, int]] = []
    for item in input_value:
        if (
            isinstance(item, (tuple, list))
            and len(item) == 2
            and isinstance(item[0], int)
            and isinstance(item[1], int)
        ):
            parsed.append((int(item[0]), int(item[1])))
            continue
        raise TypeError("intervals query input must contain int pairs")
    return parsed


def _java_intervals_literal(intervals: list[tuple[int, int]]) -> str:
    rows = ", ".join(
        "{" + f"{_long_literal(a)}, {_long_literal(b)}" + "}"
        for a, b in intervals
    )
    return "new long[][]{" + rows + "}"


def _rust_intervals_literal(intervals: list[tuple[int, int]]) -> str:
    rows = ", ".join(
        "(" + f"{_i64_literal(a)}, {_i64_literal(b)}" + ")"
        for a, b in intervals
    )
    return "vec![" + rows + "]"


def _run_java_f(
    javac: str,
    java: str,
    code: str,
    intervals: list[tuple[int, int]],
) -> int:
    intervals_lit = _java_intervals_literal(intervals)
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    long[][] intervals = {intervals_lit};\n"
        "    System.out.print(f(intervals));\n"
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


def _run_rust_f(
    rustc: str,
    code: str,
    intervals: list[tuple[int, int]],
) -> int:
    intervals_lit = _rust_intervals_literal(intervals)
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let intervals: Vec<(i64, i64)> = {intervals_lit};\n"
        "    println!(\"{}\", f(&intervals));\n"
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
def test_intervals_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_intervals_task(rng=random.Random(42))
    spec = IntervalsSpec.model_validate(task.spec)
    java_code = render_intervals_java(spec, func_name="f")

    for query in task.queries:
        intervals = _parse_query_input(query.input)
        expected = eval_intervals(spec, intervals)
        actual = _run_java_f(javac, java, java_code, intervals)
        assert actual == expected


@pytest.mark.full
def test_intervals_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_intervals_task(rng=random.Random(99))
    spec = IntervalsSpec.model_validate(task.spec)
    rust_code = render_intervals_rust(spec, func_name="f")

    for query in task.queries:
        intervals = _parse_query_input(query.input)
        expected = eval_intervals(spec, intervals)
        actual = _run_rust_f(rustc, rust_code, intervals)
        assert actual == expected


@pytest.mark.full
def test_intervals_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    sample_inputs = (
        [],
        [(0, 0)],
        [(1, 3)],
        [(3, 1)],
        [(-2, 2), (2, 5)],
        [(-5, -5), (-5, -1), (-3, -2)],
        [(7, 4), (4, 1), (1, -2), (-2, -5)],
        [(1, 4), (2, 6), (3, 7), (4, 8)],
    )

    for _ in range(8):
        spec = sample_intervals_spec(IntervalsAxes(), rng=rng)
        java_code = render_intervals_java(spec, func_name="f")
        rust_code = render_intervals_rust(spec, func_name="f")
        for intervals in sample_inputs:
            expected = eval_intervals(spec, intervals)
            assert _run_java_f(javac, java, java_code, intervals) == expected
            assert _run_rust_f(rustc, rust_code, intervals) == expected
