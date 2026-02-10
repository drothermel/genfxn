import random
import subprocess
import tempfile
from pathlib import Path

import pytest
from helpers import require_java_runtime, require_rust_runtime

from genfxn.bitops.eval import eval_bitops
from genfxn.bitops.models import BitInstruction, BitOp, BitopsAxes, BitopsSpec
from genfxn.bitops.sampler import sample_bitops_spec
from genfxn.bitops.task import generate_bitops_task
from genfxn.langs.java.bitops import render_bitops as render_bitops_java
from genfxn.langs.rust.bitops import render_bitops as render_bitops_rust


def _run_java_f(javac: str, java: str, code: str, x: int) -> int:
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    long x = {x}L;\n"
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
def test_bitops_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_bitops_task(rng=random.Random(42))
    spec = BitopsSpec.model_validate(task.spec)
    java_code = render_bitops_java(spec, func_name="f")

    for query in task.queries:
        x = int(query.input)
        expected = eval_bitops(spec, x)
        actual = _run_java_f(javac, java, java_code, x)
        assert actual == expected


@pytest.mark.full
def test_bitops_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_bitops_task(rng=random.Random(99))
    spec = BitopsSpec.model_validate(task.spec)
    rust_code = render_bitops_rust(spec, func_name="f")

    for query in task.queries:
        x = int(query.input)
        expected = eval_bitops(spec, x)
        actual = _run_rust_f(rustc, rust_code, x)
        assert actual == expected


@pytest.mark.full
def test_bitops_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    for _ in range(8):
        spec = sample_bitops_spec(BitopsAxes(), rng=rng)
        java_code = render_bitops_java(spec, func_name="f")
        rust_code = render_bitops_rust(spec, func_name="f")
        for x in (0, 1, -1, 7, -13, 255, -512, 1024):
            expected = eval_bitops(spec, x)
            assert _run_java_f(javac, java, java_code, x) == expected
            assert _run_rust_f(rustc, rust_code, x) == expected


@pytest.mark.full
def test_bitops_runtime_parity_forced_width_and_op_boundaries() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    cases: tuple[tuple[BitopsSpec, tuple[int, ...]], ...] = (
        (
            BitopsSpec(
                width_bits=63,
                operations=[
                    BitInstruction(op=BitOp.ROTL, arg=126),
                    BitInstruction(op=BitOp.SHL, arg=64),
                    BitInstruction(op=BitOp.ROTR, arg=-1),
                    BitInstruction(op=BitOp.XOR_MASK, arg=(1 << 62) - 1),
                ],
            ),
            (0, 1, -1, (1 << 62) - 1, -(1 << 62)),
        ),
        (
            BitopsSpec(
                width_bits=1,
                operations=[
                    BitInstruction(op=BitOp.NOT),
                    BitInstruction(op=BitOp.POPCOUNT),
                    BitInstruction(op=BitOp.PARITY),
                    BitInstruction(op=BitOp.SHR_LOGICAL, arg=7),
                ],
            ),
            (-3, -1, 0, 1, 2),
        ),
    )

    for spec, sample_inputs in cases:
        java_code = render_bitops_java(spec, func_name="f")
        rust_code = render_bitops_rust(spec, func_name="f")
        for x in sample_inputs:
            expected = eval_bitops(spec, x)
            assert _run_java_f(javac, java, java_code, x) == expected
            assert _run_rust_f(rustc, rust_code, x) == expected
