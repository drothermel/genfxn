import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from genfxn.fsm.eval import eval_fsm
from genfxn.fsm.models import FsmAxes, FsmSpec
from genfxn.fsm.sampler import sample_fsm_spec
from genfxn.fsm.task import generate_fsm_task
from genfxn.langs.java.fsm import render_fsm as render_fsm_java
from genfxn.langs.rust.fsm import render_fsm as render_fsm_rust


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


def _run_java_f(
    javac: str, java: str, code: str, xs: list[int]
) -> int:
    xs_lit = ", ".join(str(x) for x in xs)
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
def test_fsm_java_runtime_parity() -> None:
    javac, java = _require_java_runtime()
    task = generate_fsm_task(rng=random.Random(42))
    spec = FsmSpec.model_validate(task.spec)
    java_code = render_fsm_java(spec, func_name="f")

    for query in task.queries:
        expected = eval_fsm(spec, list(query.input))
        actual = _run_java_f(javac, java, java_code, list(query.input))
        assert actual == expected


@pytest.mark.full
def test_fsm_rust_runtime_parity() -> None:
    rustc = _require_rust_runtime()
    task = generate_fsm_task(rng=random.Random(99))
    spec = FsmSpec.model_validate(task.spec)
    rust_code = render_fsm_rust(spec, func_name="f")

    for query in task.queries:
        expected = eval_fsm(spec, list(query.input))
        actual = _run_rust_f(rustc, rust_code, list(query.input))
        assert actual == expected


@pytest.mark.full
def test_fsm_runtime_parity_across_sampled_specs() -> None:
    javac, java = _require_java_runtime()
    rustc = _require_rust_runtime()

    rng = random.Random(77)
    for _ in range(8):
        spec = sample_fsm_spec(FsmAxes(), rng=rng)
        java_code = render_fsm_java(spec, func_name="f")
        rust_code = render_fsm_rust(spec, func_name="f")
        for xs in ([], [0], [1, 2], [-3, 4, 5], [7, 7, 7, 7]):
            try:
                expected = eval_fsm(spec, xs)
            except ValueError:
                continue
            assert _run_java_f(javac, java, java_code, xs) == expected
            assert _run_rust_f(rustc, rust_code, xs) == expected
