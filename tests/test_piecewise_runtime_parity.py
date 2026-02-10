import random
import subprocess
import tempfile
from pathlib import Path

import pytest
from helpers import require_java_runtime, require_rust_runtime

from genfxn.core.predicates import PredicateGe, PredicateLt
from genfxn.langs.java.piecewise import (
    render_piecewise as render_piecewise_java,
)
from genfxn.langs.rust.piecewise import (
    render_piecewise as render_piecewise_rust,
)
from genfxn.piecewise.eval import eval_piecewise
from genfxn.piecewise.models import (
    Branch,
    ExprAbs,
    ExprAffine,
    ExprMod,
    ExprQuadratic,
    PiecewiseAxes,
    PiecewiseSpec,
)
from genfxn.piecewise.sampler import sample_piecewise_spec
from genfxn.piecewise.task import generate_piecewise_task


def _run_java_f(javac: str, java: str, code: str, x: int) -> int:
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    int x = {x};\n"
        "    System.out.print(f(x));\n"
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


def _run_rust_f(rustc: str, code: str, x: int) -> int:
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let x: i64 = {x}i64;\n"
        "    println!(\"{}\", f(x));\n"
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
def test_piecewise_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_piecewise_task(rng=random.Random(42))
    spec = PiecewiseSpec.model_validate(task.spec)
    java_code = render_piecewise_java(spec, func_name="f")

    for query in task.queries:
        x = int(query.input)
        expected = eval_piecewise(spec, x)
        actual = _run_java_f(javac, java, java_code, x)
        assert actual == expected


@pytest.mark.full
def test_piecewise_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_piecewise_task(rng=random.Random(99))
    spec = PiecewiseSpec.model_validate(task.spec)
    rust_code = render_piecewise_rust(spec, func_name="f")

    for query in task.queries:
        x = int(query.input)
        expected = eval_piecewise(spec, x)
        actual = _run_rust_f(rustc, rust_code, x)
        assert actual == expected


@pytest.mark.full
def test_piecewise_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    axes = PiecewiseAxes(
        value_range=(-25, 25),
        threshold_range=(-10, 10),
        coeff_range=(-5, 5),
        divisor_range=(2, 8),
    )
    for _ in range(8):
        spec = sample_piecewise_spec(axes, rng=rng)
        java_code = render_piecewise_java(spec, func_name="f")
        rust_code = render_piecewise_rust(spec, func_name="f")
        for x in (-25, -13, -1, 0, 1, 7, 19, 25):
            expected = eval_piecewise(spec, x)
            assert _run_java_f(javac, java, java_code, x) == expected
            assert _run_rust_f(rustc, rust_code, x) == expected


@pytest.mark.full
def test_piecewise_runtime_parity_forced_expression_coverage() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    always_true = PredicateGe(value=-10_000)

    specs: tuple[PiecewiseSpec, ...] = (
        PiecewiseSpec(
            branches=[
                Branch(condition=always_true, expr=ExprAffine(a=2, b=-3))
            ],
            default_expr=ExprAffine(a=0, b=0),
        ),
        PiecewiseSpec(
            branches=[
                Branch(
                    condition=always_true,
                    expr=ExprQuadratic(a=1, b=-2, c=5),
                )
            ],
            default_expr=ExprAffine(a=0, b=0),
        ),
        PiecewiseSpec(
            branches=[Branch(condition=always_true, expr=ExprAbs(a=-3, b=4))],
            default_expr=ExprAffine(a=0, b=0),
        ),
        PiecewiseSpec(
            branches=[
                Branch(
                    condition=always_true,
                    expr=ExprMod(divisor=5, a=7, b=-1),
                )
            ],
            default_expr=ExprAffine(a=0, b=0),
        ),
    )
    for spec in specs:
        java_code = render_piecewise_java(spec, func_name="f")
        rust_code = render_piecewise_rust(spec, func_name="f")
        for x in (-9, -1, 0, 3, 9):
            expected = eval_piecewise(spec, x)
            assert _run_java_f(javac, java, java_code, x) == expected
            assert _run_rust_f(rustc, rust_code, x) == expected


@pytest.mark.full
def test_piecewise_runtime_parity_overflow_int32_contract() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    always_true = PredicateGe(value=-2_147_483_648)
    spec = PiecewiseSpec(
        branches=[
            Branch(
                condition=always_true,
                expr=ExprQuadratic(a=1, b=0, c=0),
            )
        ],
        default_expr=ExprAffine(a=0, b=0),
    )
    java_code = render_piecewise_java(spec, func_name="f")
    rust_code = render_piecewise_rust(spec, func_name="f")

    x = 50_000
    expected = eval_piecewise(spec, x)
    assert expected == -1_794_967_296
    assert _run_java_f(javac, java, java_code, x) == expected
    assert _run_rust_f(rustc, rust_code, x) == expected


@pytest.mark.full
def test_piecewise_runtime_parity_int32_boundary_cases() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    always_true = PredicateGe(value=-10_000)

    cases: tuple[tuple[PiecewiseSpec, tuple[int, ...]], ...] = (
        (
            PiecewiseSpec(
                branches=[
                    Branch(condition=always_true, expr=ExprAffine(a=1, b=0))
                ],
                default_expr=ExprAffine(a=0, b=0),
            ),
            (2_000_000_000, 2_147_483_647),
        ),
        (
            PiecewiseSpec(
                branches=[
                    Branch(
                        condition=always_true,
                        expr=ExprQuadratic(a=1, b=0, c=0),
                    )
                ],
                default_expr=ExprAffine(a=0, b=0),
            ),
            (50_000,),
        ),
        (
            PiecewiseSpec(
                branches=[
                    Branch(
                        condition=always_true,
                        expr=ExprAffine(a=50_000, b=0),
                    )
                ],
                default_expr=ExprAffine(a=0, b=0),
            ),
            (50_000,),
        ),
    )

    for spec, inputs in cases:
        java_code = render_piecewise_java(spec, func_name="f")
        rust_code = render_piecewise_rust(spec, func_name="f")
        for x in inputs:
            expected = eval_piecewise(spec, x)
            assert _run_java_f(javac, java, java_code, x) == expected
            assert _run_rust_f(rustc, rust_code, x) == expected


@pytest.mark.full
def test_piecewise_java_compiles_with_oversized_int_literals() -> None:
    javac, java = require_java_runtime()
    spec = PiecewiseSpec(
        branches=[
            Branch(
                condition=PredicateLt(value=3_000_000_001),
                expr=ExprMod(
                    divisor=3_000_000_003,
                    a=-3_000_000_005,
                    b=3_000_000_007,
                ),
            )
        ],
        default_expr=ExprQuadratic(
            a=3_000_000_011,
            b=-3_000_000_013,
            c=3_000_000_017,
        ),
    )
    java_code = render_piecewise_java(spec, func_name="f")

    result = _run_java_f(javac, java, java_code, 7)
    assert isinstance(result, int)
