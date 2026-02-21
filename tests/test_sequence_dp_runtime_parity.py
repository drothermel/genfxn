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

from genfxn.langs.java.sequence_dp import (
    render_sequence_dp as render_sequence_dp_java,
)
from genfxn.langs.rust.sequence_dp import (
    render_sequence_dp as render_sequence_dp_rust,
)
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.sequence_dp.models import (
    OutputMode,
    PredicateAbsDiffLe,
    PredicateEq,
    PredicateModEq,
    SequenceDpAxes,
    SequenceDpSpec,
    TemplateType,
    TieBreakOrder,
)
from genfxn.sequence_dp.sampler import sample_sequence_dp_spec
from genfxn.sequence_dp.task import generate_sequence_dp_task


def _long_literal(value: int) -> str:
    if value == -(1 << 63):
        return "Long.MIN_VALUE"
    return f"{value}L"


def _i64_literal(value: int) -> str:
    if value == -(1 << 63):
        return "i64::MIN"
    return f"{value}i64"


def _parse_query_input(input_value: Any) -> tuple[list[int], list[int]]:
    if not isinstance(input_value, dict):
        raise TypeError("sequence_dp query input must be a dict")
    a_vals = input_value.get("a")
    b_vals = input_value.get("b")
    if not isinstance(a_vals, list) or not isinstance(b_vals, list):
        raise TypeError("sequence_dp query input must contain list fields")
    return list(a_vals), list(b_vals)


def _run_java_f(
    javac: str,
    java: str,
    code: str,
    a_vals: list[int],
    b_vals: list[int],
) -> int:
    a_lit = ", ".join(_long_literal(value) for value in a_vals)
    b_lit = ", ".join(_long_literal(value) for value in b_vals)
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    long[] a = new long[]{{{a_lit}}};\n"
        f"    long[] b = new long[]{{{b_lit}}};\n"
        "    System.out.print(f(a, b));\n"
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
    a_vals: list[int],
    b_vals: list[int],
    *,
    optimize: bool = True,
) -> int:
    a_lit = ", ".join(_i64_literal(value) for value in a_vals)
    b_lit = ", ".join(_i64_literal(value) for value in b_vals)
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let a: Vec<i64> = vec![{a_lit}];\n"
        f"    let b: Vec<i64> = vec![{b_lit}];\n"
        '    println!("{}", f(&a, &b));\n'
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src = tmp / "main.rs"
        out = tmp / "main_bin"
        src.write_text(main_src, encoding="utf-8")
        compile_cmd = [rustc, str(src)]
        if optimize:
            compile_cmd.append("-O")
        compile_cmd.extend(["-o", str(out)])
        run_checked_subprocess(
            compile_cmd,
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [str(out)],
            cwd=tmp,
        )
        return int(proc.stdout.strip())


@pytest.mark.full
def test_sequence_dp_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_sequence_dp_task(rng=random.Random(42))
    spec = SequenceDpSpec.model_validate(task.spec)
    java_code = render_sequence_dp_java(spec, func_name="f")

    for query in task.queries:
        a_vals, b_vals = _parse_query_input(query.input)
        expected = eval_sequence_dp(spec, a_vals, b_vals)
        actual = _run_java_f(javac, java, java_code, a_vals, b_vals)
        assert actual == expected


@pytest.mark.full
def test_sequence_dp_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_sequence_dp_task(rng=random.Random(99))
    spec = SequenceDpSpec.model_validate(task.spec)
    rust_code = render_sequence_dp_rust(spec, func_name="f")

    for query in task.queries:
        a_vals, b_vals = _parse_query_input(query.input)
        expected = eval_sequence_dp(spec, a_vals, b_vals)
        actual = _run_rust_f(rustc, rust_code, a_vals, b_vals)
        assert actual == expected


@pytest.mark.full
def test_sequence_dp_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    sample_inputs = (
        ([], []),
        ([0], [0]),
        ([], [1, 2]),
        ([1, 2], []),
        ([1, 2, 3], [1, 2, 3]),
        ([-5, 0, 5], [5, 0, -5]),
        ([7, 7, 7, 7], [7]),
        ([1, -2, 3, -4, 5], [-1, 2, -3, 4, -5]),
    )

    for _ in range(8):
        spec = sample_sequence_dp_spec(SequenceDpAxes(), rng=rng)
        java_code = render_sequence_dp_java(spec, func_name="f")
        rust_code = render_sequence_dp_rust(spec, func_name="f")
        for a_vals, b_vals in sample_inputs:
            expected = eval_sequence_dp(spec, a_vals, b_vals)
            assert _run_java_f(javac, java, java_code, a_vals, b_vals) == (
                expected
            )
            assert _run_rust_f(rustc, rust_code, a_vals, b_vals) == expected


@pytest.mark.full
def test_sequence_dp_runtime_parity_forced_predicate_output_coverage() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    CaseInputPairs = list[tuple[list[int], list[int]]]
    cases: tuple[tuple[SequenceDpSpec, CaseInputPairs], ...] = (
        (
            SequenceDpSpec(
                template=TemplateType.GLOBAL,
                output_mode=OutputMode.SCORE,
                match_predicate=PredicateEq(),
                match_score=3,
                mismatch_score=-2,
                gap_score=-1,
                step_tie_break=TieBreakOrder.DIAG_UP_LEFT,
            ),
            [([1, 2, 3], [1, 2, 3]), ([1, 2, 3], [3, 2, 1])],
        ),
        (
            SequenceDpSpec(
                template=TemplateType.LOCAL,
                output_mode=OutputMode.ALIGNMENT_LEN,
                match_predicate=PredicateAbsDiffLe(max_diff=1),
                match_score=4,
                mismatch_score=-3,
                gap_score=-1,
                step_tie_break=TieBreakOrder.LEFT_DIAG_UP,
            ),
            [([0, 1, 2, 3], [0, 2, 4]), ([5, 5, 5], [4, 6, 5])],
        ),
        (
            SequenceDpSpec(
                template=TemplateType.GLOBAL,
                output_mode=OutputMode.GAP_COUNT,
                match_predicate=PredicateModEq(divisor=3, remainder=1),
                match_score=2,
                mismatch_score=-1,
                gap_score=-2,
                step_tie_break=TieBreakOrder.UP_LEFT_DIAG,
            ),
            [([1, 4, 7], [1, 2, 3]), ([2, 5], [8, 11, 14])],
        ),
    )

    for spec, query_inputs in cases:
        java_code = render_sequence_dp_java(spec, func_name="f")
        rust_code = render_sequence_dp_rust(spec, func_name="f")
        for a_vals, b_vals in query_inputs:
            expected = eval_sequence_dp(spec, a_vals, b_vals)
            assert _run_java_f(javac, java, java_code, a_vals, b_vals) == (
                expected
            )
            assert _run_rust_f(rustc, rust_code, a_vals, b_vals) == expected


@pytest.mark.full
def test_sequence_dp_abs_diff_extreme_values_parity() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    spec = SequenceDpSpec(
        template=TemplateType.GLOBAL,
        output_mode=OutputMode.SCORE,
        match_predicate=PredicateAbsDiffLe(max_diff=0),
        match_score=5,
        mismatch_score=-4,
        gap_score=-1,
        step_tie_break=TieBreakOrder.DIAG_UP_LEFT,
    )
    a_vals = [-(1 << 63)]
    b_vals = [(1 << 63) - 1]
    expected = eval_sequence_dp(spec, a_vals, b_vals)

    java_code = render_sequence_dp_java(spec, func_name="f")
    rust_code = render_sequence_dp_rust(spec, func_name="f")
    assert _run_java_f(javac, java, java_code, a_vals, b_vals) == expected
    assert _run_rust_f(rustc, rust_code, a_vals, b_vals) == expected


@pytest.mark.full
def test_sequence_dp_runtime_parity_overflow_adjacent_cases() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    max_i64 = (1 << 63) - 1
    min_i64 = -(1 << 63)
    score_boundary_spec = SequenceDpSpec(
        template=TemplateType.GLOBAL,
        output_mode=OutputMode.SCORE,
        match_predicate=PredicateEq(),
        match_score=1,
        mismatch_score=-1,
        gap_score=min_i64,
        step_tie_break=TieBreakOrder.DIAG_UP_LEFT,
    )
    score_boundary_inputs = ([1, 1], [])

    predicate_overflow_spec = SequenceDpSpec(
        template=TemplateType.GLOBAL,
        output_mode=OutputMode.SCORE,
        match_predicate=PredicateModEq(divisor=3, remainder=1),
        match_score=9,
        mismatch_score=-4,
        gap_score=-2,
        step_tie_break=TieBreakOrder.DIAG_UP_LEFT,
    )
    predicate_overflow_inputs = ([max_i64], [-1])

    cases: tuple[tuple[SequenceDpSpec, tuple[list[int], list[int]]], ...] = (
        (score_boundary_spec, score_boundary_inputs),
        (predicate_overflow_spec, predicate_overflow_inputs),
    )

    for spec, (a_vals, b_vals) in cases:
        expected = eval_sequence_dp(spec, a_vals, b_vals)
        java_code = render_sequence_dp_java(spec, func_name="f")
        rust_code = render_sequence_dp_rust(spec, func_name="f")
        assert _run_java_f(javac, java, java_code, a_vals, b_vals) == expected
        assert (
            _run_rust_f(
                rustc,
                rust_code,
                a_vals,
                b_vals,
                optimize=False,
            )
            == expected
        )
        assert (
            _run_rust_f(
                rustc,
                rust_code,
                a_vals,
                b_vals,
                optimize=True,
            )
            == expected
        )
