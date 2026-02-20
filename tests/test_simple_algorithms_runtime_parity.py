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
from pydantic import TypeAdapter

from genfxn.core.predicates import PredicateGe, PredicateOdd
from genfxn.core.transforms import TransformNegate, TransformShift
from genfxn.langs.java.simple_algorithms import (
    render_simple_algorithms as render_simple_algorithms_java,
)
from genfxn.langs.rust.simple_algorithms import (
    render_simple_algorithms as render_simple_algorithms_rust,
)
from genfxn.simple_algorithms.eval import eval_simple_algorithms
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)
from genfxn.simple_algorithms.sampler import sample_simple_algorithms_spec
from genfxn.simple_algorithms.task import generate_simple_algorithms_task

_simple_algorithms_spec_adapter = TypeAdapter(SimpleAlgorithmsSpec)


def _parse_query_input(input_value: Any) -> list[int]:
    if not isinstance(input_value, list):
        raise TypeError("simple_algorithms query input must be list[int]")
    if not all(isinstance(v, int) for v in input_value):
        raise TypeError("simple_algorithms query input must be list[int]")
    return [int(v) for v in input_value]


def _run_java_f(javac: str, java: str, code: str, xs: list[int]) -> int:
    xs_lit = ", ".join(f"{x}" for x in xs)
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    int[] xs = new int[]{{{xs_lit}}};\n"
        "    System.out.print(f(xs));\n"
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


def _run_rust_f(rustc: str, code: str, xs: list[int]) -> int:
    xs_lit = ", ".join(f"{x}i64" for x in xs)
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
        '    println!("{}", f(&xs));\n'
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
def test_simple_algorithms_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_simple_algorithms_task(rng=random.Random(42))
    spec = _simple_algorithms_spec_adapter.validate_python(
        task.spec,
        strict=True,
    )
    java_code = render_simple_algorithms_java(spec, func_name="f")

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_simple_algorithms(spec, xs)
        actual = _run_java_f(javac, java, java_code, xs)
        assert actual == expected


@pytest.mark.full
def test_simple_algorithms_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_simple_algorithms_task(rng=random.Random(99))
    spec = _simple_algorithms_spec_adapter.validate_python(
        task.spec,
        strict=True,
    )
    rust_code = render_simple_algorithms_rust(spec, func_name="f")

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_simple_algorithms(spec, xs)
        actual = _run_rust_f(rustc, rust_code, xs)
        assert actual == expected


@pytest.mark.full
def test_simple_algorithms_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    axes = SimpleAlgorithmsAxes(
        value_range=(-20, 20),
        list_length_range=(0, 10),
        target_range=(-15, 15),
        window_size_range=(1, 8),
    )
    sample_inputs = (
        [],
        [0],
        [1, -1],
        [2, 2, 2],
        [5, -4, 3, -2, 1],
        [9, 8, 7, 6, 5, 4],
    )
    for _ in range(8):
        spec = sample_simple_algorithms_spec(axes, rng=rng)
        java_code = render_simple_algorithms_java(spec, func_name="f")
        rust_code = render_simple_algorithms_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_simple_algorithms(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected


@pytest.mark.full
def test_simple_algorithms_runtime_parity_forced_templates_and_modes() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    cases: tuple[tuple[SimpleAlgorithmsSpec, tuple[list[int], ...]], ...] = (
        (
            MostFrequentSpec(
                tie_break=TieBreakMode.FIRST_SEEN,
                empty_default=-1,
                pre_filter=PredicateGe(value=0),
                pre_transform=TransformShift(offset=1),
                tie_default=99,
            ),
            ([], [1, 2, 1, 2], [-5, -2]),
        ),
        (
            CountPairsSumSpec(
                target=5,
                counting_mode=CountingMode.UNIQUE_VALUES,
                no_result_default=-7,
                short_list_default=-1,
            ),
            ([], [2, 3, 2, 3, 1, 4], [10, 11, 12]),
        ),
        (
            CountPairsSumSpec(
                target=4,
                counting_mode=CountingMode.ALL_INDICES,
            ),
            ([1, 3, 1, 3], [2, 2, 2]),
        ),
        (
            MaxWindowSumSpec(
                k=3,
                invalid_k_default=-5,
                empty_default=17,
                pre_filter=PredicateOdd(),
                pre_transform=TransformNegate(),
            ),
            ([], [2, 4], [1, 3, 5, 7], [1, 2, 3, 4]),
        ),
    )

    for spec, sample_inputs in cases:
        java_code = render_simple_algorithms_java(spec, func_name="f")
        rust_code = render_simple_algorithms_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_simple_algorithms(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected


@pytest.mark.full
def test_simple_algorithms_runtime_parity_overflow_int32_contract() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = MaxWindowSumSpec(k=2, invalid_k_default=-1)
    xs = [2_000_000_000, 2_000_000_000]

    java_code = render_simple_algorithms_java(spec, func_name="f")
    rust_code = render_simple_algorithms_rust(spec, func_name="f")
    expected = eval_simple_algorithms(spec, xs)

    assert expected == -294_967_296
    assert _run_java_f(javac, java, java_code, xs) == expected
    assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_simple_algorithms_runtime_parity_int32_boundary_cases() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    int32_max = (1 << 31) - 1
    int32_min = -(1 << 31)
    wrapped_50k_square = -1_794_967_296

    cases: tuple[tuple[SimpleAlgorithmsSpec, list[int]], ...] = (
        (
            MaxWindowSumSpec(
                k=2,
                invalid_k_default=-1,
            ),
            [2_000_000_000, 147_483_647, -2_000_000_000, 147_483_647],
        ),
        (
            CountPairsSumSpec(
                target=int32_min,
                counting_mode=CountingMode.ALL_INDICES,
            ),
            [int32_max, 1, 0],
        ),
        (
            CountPairsSumSpec(
                target=wrapped_50k_square,
                counting_mode=CountingMode.ALL_INDICES,
            ),
            [2_000_000_000, 500_000_000],
        ),
    )

    for spec, xs in cases:
        java_code = render_simple_algorithms_java(spec, func_name="f")
        rust_code = render_simple_algorithms_rust(spec, func_name="f")
        expected = eval_simple_algorithms(spec, xs)
        assert _run_java_f(javac, java, java_code, xs) == expected
        assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_simple_algorithms_runtime_parity_predicate_i32_wrap() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = MostFrequentSpec(
        tie_break=TieBreakMode.SMALLEST,
        empty_default=-1,
        pre_filter=PredicateGe(value=3_000_000_005),
    )
    xs = [0]

    java_code = render_simple_algorithms_java(spec, func_name="f")
    rust_code = render_simple_algorithms_rust(spec, func_name="f")
    expected = eval_simple_algorithms(spec, xs)

    assert expected == 0
    assert _run_java_f(javac, java, java_code, xs) == expected
    assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_simple_algorithms_runtime_parity_with_oversized_int_literals() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    cases: tuple[tuple[SimpleAlgorithmsSpec, tuple[list[int], ...]], ...] = (
        (
            MostFrequentSpec(
                tie_break=TieBreakMode.SMALLEST,
                empty_default=3_000_000_001,
                tie_default=-3_000_000_003,
                pre_filter=PredicateGe(value=0),
                pre_transform=TransformShift(offset=3_000_000_007),
            ),
            ([], [1, 1, 2, 2], [-2, -1, -3]),
        ),
        (
            CountPairsSumSpec(
                target=3_000_000_011,
                counting_mode=CountingMode.ALL_INDICES,
                no_result_default=-3_000_000_013,
                short_list_default=3_000_000_015,
                pre_transform=TransformShift(offset=3_000_000_017),
            ),
            ([], [1], [1, 2, 3], [-10, 0, 10, 20]),
        ),
    )

    for spec, inputs in cases:
        java_code = render_simple_algorithms_java(spec, func_name="f")
        rust_code = render_simple_algorithms_rust(spec, func_name="f")
        for xs in inputs:
            expected = eval_simple_algorithms(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected
