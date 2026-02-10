import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from helpers import require_java_runtime, require_rust_runtime
from pydantic import TypeAdapter

from genfxn.core.predicates import (
    PredicateEven,
    PredicateGe,
    PredicateLt,
    PredicateModEq,
)
from genfxn.core.transforms import (
    TransformAbs,
    TransformClip,
    TransformIdentity,
    TransformNegate,
    TransformScale,
    TransformShift,
)
from genfxn.langs.java.stateful import render_stateful as render_stateful_java
from genfxn.langs.rust.stateful import render_stateful as render_stateful_rust
from genfxn.stateful.eval import eval_stateful
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulAxes,
    StatefulSpec,
    ToggleSumSpec,
)
from genfxn.stateful.sampler import sample_stateful_spec
from genfxn.stateful.task import generate_stateful_task

_stateful_spec_adapter = TypeAdapter(StatefulSpec)


def _parse_query_input(input_value: Any) -> list[int]:
    if not isinstance(input_value, list):
        raise TypeError("stateful query input must be list[int]")
    if not all(isinstance(v, int) for v in input_value):
        raise TypeError("stateful query input must be list[int]")
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
    xs_lit = ", ".join(f"{x}i64" for x in xs)
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
def test_stateful_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_stateful_task(rng=random.Random(42))
    spec = _stateful_spec_adapter.validate_python(task.spec, strict=True)
    java_code = render_stateful_java(spec, func_name="f")

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_stateful(spec, xs)
        actual = _run_java_f(javac, java, java_code, xs)
        assert actual == expected


@pytest.mark.full
def test_stateful_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_stateful_task(rng=random.Random(99))
    spec = _stateful_spec_adapter.validate_python(task.spec, strict=True)
    rust_code = render_stateful_rust(spec, func_name="f")

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_stateful(spec, xs)
        actual = _run_rust_f(rustc, rust_code, xs)
        assert actual == expected


@pytest.mark.full
def test_stateful_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    axes = StatefulAxes(
        value_range=(-15, 15),
        list_length_range=(0, 8),
        threshold_range=(-10, 10),
        divisor_range=(2, 8),
        shift_range=(-4, 4),
        scale_range=(-3, 3),
    )
    sample_inputs = (
        [],
        [0],
        [1, -1],
        [2, 2, 2],
        [-3, 0, 3, -3],
        [5, -4, 3, -2, 1],
    )
    for _ in range(8):
        spec = sample_stateful_spec(axes, rng=rng)
        java_code = render_stateful_java(spec, func_name="f")
        rust_code = render_stateful_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_stateful(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected


@pytest.mark.full
def test_stateful_runtime_parity_forced_templates() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    cases: tuple[tuple[StatefulSpec, tuple[list[int], ...]], ...] = (
        (
            ConditionalLinearSumSpec(
                predicate=PredicateEven(),
                true_transform=TransformShift(offset=2),
                false_transform=TransformNegate(),
                init_value=3,
            ),
            ([], [2, -1, 4], [1, 1, 2]),
        ),
        (
            ResettingBestPrefixSumSpec(
                reset_predicate=PredicateLt(value=0),
                init_value=1,
                value_transform=TransformScale(factor=2),
            ),
            ([1, 2, -1, 3], [-2, 5, 6], [0, 0, 0]),
        ),
        (
            LongestRunSpec(
                match_predicate=PredicateModEq(divisor=3, remainder=1),
            ),
            ([], [1, 4, 7, 2, 10], [2, 5, 8]),
        ),
        (
            ToggleSumSpec(
                toggle_predicate=PredicateEven(),
                on_transform=TransformAbs(),
                off_transform=TransformShift(offset=-1),
                init_value=0,
            ),
            ([2, 3, -4, 5, 6], [1, 3, 5], [2, 2, 2, 2]),
        ),
    )

    for spec, sample_inputs in cases:
        java_code = render_stateful_java(spec, func_name="f")
        rust_code = render_stateful_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_stateful(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected


@pytest.mark.full
def test_stateful_runtime_parity_overflow_int32_contract() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = ConditionalLinearSumSpec(
        predicate=PredicateGe(value=-2_147_483_648),
        true_transform=TransformIdentity(),
        false_transform=TransformIdentity(),
        init_value=0,
    )
    xs = [2_000_000_000, 2_000_000_000]

    java_code = render_stateful_java(spec, func_name="f")
    rust_code = render_stateful_rust(spec, func_name="f")
    expected = eval_stateful(spec, xs)

    assert expected == -294_967_296
    assert _run_java_f(javac, java, java_code, xs) == expected
    assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_stateful_runtime_parity_int32_boundary_cases() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    int32_max = (1 << 31) - 1

    cases: tuple[tuple[StatefulSpec, list[int]], ...] = (
        (
            ConditionalLinearSumSpec(
                predicate=PredicateGe(value=0),
                true_transform=TransformShift(offset=0),
                false_transform=TransformNegate(),
                init_value=0,
            ),
            [2_000_000_000, 147_483_647, 0],
        ),
        (
            ConditionalLinearSumSpec(
                predicate=PredicateGe(value=0),
                true_transform=TransformScale(factor=50_000),
                false_transform=TransformShift(offset=0),
                init_value=0,
            ),
            [50_000],
        ),
        (
            ResettingBestPrefixSumSpec(
                reset_predicate=PredicateLt(value=0),
                init_value=int32_max,
                value_transform=TransformShift(offset=1),
            ),
            [1, -1, 1],
        ),
    )

    for spec, xs in cases:
        java_code = render_stateful_java(spec, func_name="f")
        rust_code = render_stateful_rust(spec, func_name="f")
        expected = eval_stateful(spec, xs)
        assert _run_java_f(javac, java, java_code, xs) == expected
        assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_stateful_runtime_parity_predicate_int32_constant_wrap() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = ConditionalLinearSumSpec(
        predicate=PredicateGe(value=3_000_000_005),
        true_transform=TransformIdentity(),
        false_transform=TransformShift(offset=-9),
        init_value=0,
    )
    xs = [0]

    java_code = render_stateful_java(spec, func_name="f")
    rust_code = render_stateful_rust(spec, func_name="f")
    expected = eval_stateful(spec, xs)

    assert expected == 0
    assert _run_java_f(javac, java, java_code, xs) == expected
    assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_stateful_runtime_parity_clip_wrapped_bounds() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = ConditionalLinearSumSpec(
        predicate=PredicateGe(value=-2_147_483_648),
        true_transform=TransformClip(
            low=3_000_000_000,
            high=3_000_000_100,
        ),
        false_transform=TransformIdentity(),
        init_value=0,
    )
    xs = [0]

    java_code = render_stateful_java(spec, func_name="f")
    rust_code = render_stateful_rust(spec, func_name="f")
    expected = eval_stateful(spec, xs)

    assert expected == -1_294_967_196
    assert _run_java_f(javac, java, java_code, xs) == expected
    assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_stateful_runtime_parity_with_oversized_int_literals() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = ConditionalLinearSumSpec(
        predicate=PredicateEven(),
        true_transform=TransformShift(offset=3_000_000_005),
        false_transform=TransformScale(factor=-3_000_000_007),
        init_value=3_000_000_009,
    )
    java_code = render_stateful_java(spec, func_name="f")
    rust_code = render_stateful_rust(spec, func_name="f")

    for xs in ([], [1, 2, 3], [-4, -1, 0, 2]):
        expected = eval_stateful(spec, list(xs))
        assert _run_java_f(javac, java, java_code, list(xs)) == expected
        assert _run_rust_f(rustc, rust_code, list(xs)) == expected
