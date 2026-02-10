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

from genfxn.intervals.eval import eval_intervals
from genfxn.intervals.models import (
    BoundaryMode,
    IntervalsAxes,
    IntervalsSpec,
    OperationType,
)
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
        run_checked_subprocess(
            [javac, str(src)],
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
        run_checked_subprocess(
            [rustc, str(src), "-O", "-o", str(out)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [str(out)],
            cwd=tmp,
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


@pytest.mark.full
def test_intervals_runtime_parity_forced_operation_and_boundary_modes() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    CaseInputs = tuple[list[tuple[int, int]], ...]
    cases: tuple[tuple[IntervalsSpec, CaseInputs], ...] = (
        (
            IntervalsSpec(
                operation=OperationType.TOTAL_COVERAGE,
                boundary_mode=BoundaryMode.OPEN_OPEN,
                merge_touching=False,
                endpoint_clip_abs=5,
                endpoint_quantize_step=2,
            ),
            ([(-7, 7), (1, 5), (5, 9)], [(0, 0), (0, 2)]),
        ),
        (
            IntervalsSpec(
                operation=OperationType.MERGED_COUNT,
                boundary_mode=BoundaryMode.CLOSED_OPEN,
                merge_touching=True,
                endpoint_clip_abs=20,
                endpoint_quantize_step=1,
            ),
            ([(0, 2), (2, 4), (4, 6)], [(1, 1), (1, 2), (2, 3)]),
        ),
        (
            IntervalsSpec(
                operation=OperationType.MAX_OVERLAP_COUNT,
                boundary_mode=BoundaryMode.CLOSED_CLOSED,
                merge_touching=False,
                endpoint_clip_abs=20,
                endpoint_quantize_step=1,
            ),
            ([(-1, 3), (0, 2), (1, 4)], [(-5, -3), (-4, -2)]),
        ),
        (
            IntervalsSpec(
                operation=OperationType.GAP_COUNT,
                boundary_mode=BoundaryMode.OPEN_CLOSED,
                merge_touching=False,
                endpoint_clip_abs=20,
                endpoint_quantize_step=1,
            ),
            ([(0, 2), (4, 6), (9, 12)], [(3, 1), (7, 8)]),
        ),
    )

    for spec, sample_inputs in cases:
        java_code = render_intervals_java(spec, func_name="f")
        rust_code = render_intervals_rust(spec, func_name="f")
        for intervals in sample_inputs:
            expected = eval_intervals(spec, list(intervals))
            assert _run_java_f(javac, java, java_code, list(intervals)) == (
                expected
            )
            assert _run_rust_f(rustc, rust_code, list(intervals)) == expected


@pytest.mark.full
def test_intervals_runtime_parity_total_coverage_i64_overflow() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    i64_max = (1 << 63) - 1
    spec = IntervalsSpec(
        operation=OperationType.TOTAL_COVERAGE,
        boundary_mode=BoundaryMode.CLOSED_CLOSED,
        merge_touching=True,
        endpoint_clip_abs=i64_max,
        endpoint_quantize_step=1,
    )
    intervals = [(-i64_max, i64_max)]
    java_code = render_intervals_java(spec, func_name="f")
    rust_code = render_intervals_rust(spec, func_name="f")

    expected = eval_intervals(spec, intervals)
    assert expected == -1
    assert _run_java_f(javac, java, java_code, intervals) == expected
    assert _run_rust_f(rustc, rust_code, intervals) == expected


@pytest.mark.full
def test_intervals_runtime_parity_max_overlap_end_plus_one_wrap() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    i64_max = (1 << 63) - 1
    spec = IntervalsSpec(
        operation=OperationType.MAX_OVERLAP_COUNT,
        boundary_mode=BoundaryMode.CLOSED_CLOSED,
        merge_touching=False,
        endpoint_clip_abs=i64_max,
        endpoint_quantize_step=1,
    )
    intervals = [(i64_max, i64_max)]
    java_code = render_intervals_java(spec, func_name="f")
    rust_code = render_intervals_rust(spec, func_name="f")

    expected = eval_intervals(spec, intervals)
    assert expected == 0
    assert _run_java_f(javac, java, java_code, intervals) == expected
    assert _run_rust_f(rustc, rust_code, intervals) == expected
