import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from helpers import require_java_runtime, require_rust_runtime

from genfxn.langs.java.stack_bytecode import (
    render_stack_bytecode as render_stack_bytecode_java,
)
from genfxn.langs.rust.stack_bytecode import (
    render_stack_bytecode as render_stack_bytecode_rust,
)
from genfxn.stack_bytecode.eval import eval_stack_bytecode
from genfxn.stack_bytecode.models import StackBytecodeAxes, StackBytecodeSpec
from genfxn.stack_bytecode.sampler import sample_stack_bytecode_spec
from genfxn.stack_bytecode.task import generate_stack_bytecode_task


def _parse_query_input(input_value: Any) -> list[int]:
    if not isinstance(input_value, list):
        raise TypeError("stack_bytecode query input must be list[int]")
    if not all(isinstance(v, int) for v in input_value):
        raise TypeError("stack_bytecode query input must be list[int]")
    return [int(v) for v in input_value]


def _run_java_f(
    javac: str, java: str, code: str, xs: list[int]
) -> tuple[int, int]:
    xs_lit = ", ".join(f"{x}" for x in xs)
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    int[] xs = new int[]{{{xs_lit}}};\n"
        "    int[] out = f(xs);\n"
        "    System.out.print(out[0] + \",\" + out[1]);\n"
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
        status_s, value_s = proc.stdout.strip().split(",", maxsplit=1)
        return int(status_s), int(value_s)


def _run_rust_f(rustc: str, code: str, xs: list[int]) -> tuple[int, int]:
    xs_lit = ", ".join(f"{x}i64" for x in xs)
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
        "    let out = f(&xs);\n"
        "    println!(\"{},{}\", out.0, out.1);\n"
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
        status_s, value_s = proc.stdout.strip().split(",", maxsplit=1)
        return int(status_s), int(value_s)


@pytest.mark.full
def test_stack_bytecode_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_stack_bytecode_task(rng=random.Random(42))
    spec = StackBytecodeSpec.model_validate(task.spec)
    java_code = render_stack_bytecode_java(spec, func_name="f")

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_stack_bytecode(spec, xs)
        actual = _run_java_f(javac, java, java_code, xs)
        assert actual == expected


@pytest.mark.full
def test_stack_bytecode_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_stack_bytecode_task(rng=random.Random(99))
    spec = StackBytecodeSpec.model_validate(task.spec)
    rust_code = render_stack_bytecode_rust(spec, func_name="f")

    for query in task.queries:
        xs = _parse_query_input(query.input)
        expected = eval_stack_bytecode(spec, xs)
        actual = _run_rust_f(rustc, rust_code, xs)
        assert actual == expected


@pytest.mark.full
def test_stack_bytecode_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    axes = StackBytecodeAxes(
        value_range=(-10, 10),
        list_length_range=(0, 8),
        const_range=(-6, 6),
        max_step_count_range=(20, 60),
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
        spec = sample_stack_bytecode_spec(axes, rng=rng)
        java_code = render_stack_bytecode_java(spec, func_name="f")
        rust_code = render_stack_bytecode_rust(spec, func_name="f")
        for xs in sample_inputs:
            expected = eval_stack_bytecode(spec, list(xs))
            assert _run_java_f(javac, java, java_code, list(xs)) == expected
            assert _run_rust_f(rustc, rust_code, list(xs)) == expected
