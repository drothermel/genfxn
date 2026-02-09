import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from genfxn.langs.java.sequence_dp import (
    render_sequence_dp as render_sequence_dp_java,
)
from genfxn.langs.rust.sequence_dp import (
    render_sequence_dp as render_sequence_dp_rust,
)
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.sequence_dp.models import SequenceDpAxes, SequenceDpSpec
from genfxn.sequence_dp.sampler import sample_sequence_dp_spec
from genfxn.sequence_dp.task import generate_sequence_dp_task


def _require_java_runtime() -> tuple[str, str]:
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        pytest.skip("Java runtime tools (javac/java) not available")
    assert javac is not None
    assert java is not None
    return javac, java


def _require_rust_runtime() -> str:
    rustc = shutil.which("rustc")
    if not rustc:
        pytest.skip("Rust compiler (rustc) not available")
    assert rustc is not None
    return rustc


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
    a_vals: list[int],
    b_vals: list[int],
) -> int:
    a_lit = ", ".join(_i64_literal(value) for value in a_vals)
    b_lit = ", ".join(_i64_literal(value) for value in b_vals)
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let a: Vec<i64> = vec![{a_lit}];\n"
        f"    let b: Vec<i64> = vec![{b_lit}];\n"
        "    println!(\"{}\", f(&a, &b));\n"
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
def test_sequence_dp_java_runtime_parity() -> None:
    javac, java = _require_java_runtime()
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
    rustc = _require_rust_runtime()
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
    javac, java = _require_java_runtime()
    rustc = _require_rust_runtime()

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
