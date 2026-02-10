import random
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from helpers import require_java_runtime, require_rust_runtime

from genfxn.core.string_predicates import StringPredicateLengthCmp
from genfxn.core.string_transforms import (
    StringTransformAppend,
    StringTransformIdentity,
)
from genfxn.langs.java._helpers import java_string_literal
from genfxn.langs.java.stringrules import render_stringrules as render_java
from genfxn.langs.rust._helpers import rust_string_literal
from genfxn.langs.rust.stringrules import render_stringrules as render_rust
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import (
    StringRule,
    StringRulesAxes,
    StringRulesSpec,
)
from genfxn.stringrules.sampler import sample_stringrules_spec
from genfxn.stringrules.task import generate_stringrules_task


def _parse_query_input(input_value: Any) -> str:
    if not isinstance(input_value, str):
        raise TypeError("stringrules query input must be str")
    return input_value


def _run_java_f(javac: str, java: str, code: str, s: str) -> str:
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    String s = {java_string_literal(s)};\n"
        "    System.out.print(f(s));\n"
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
        return proc.stdout


def _run_rust_f(rustc: str, code: str, s: str) -> str:
    main_src = (
        f"{code}\n"
        "fn main() {\n"
        f"    let s = {rust_string_literal(s)};\n"
        "    print!(\"{}\", f(s));\n"
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
        return proc.stdout


@pytest.mark.full
def test_stringrules_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_stringrules_task(rng=random.Random(42))
    spec = StringRulesSpec.model_validate(task.spec)
    java_code = render_java(spec, func_name="f")

    for query in task.queries:
        s = _parse_query_input(query.input)
        expected = eval_stringrules(spec, s)
        actual = _run_java_f(javac, java, java_code, s)
        assert actual == expected


@pytest.mark.full
def test_stringrules_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_stringrules_task(rng=random.Random(99))
    spec = StringRulesSpec.model_validate(task.spec)
    rust_code = render_rust(spec, func_name="f")

    for query in task.queries:
        s = _parse_query_input(query.input)
        expected = eval_stringrules(spec, s)
        actual = _run_rust_f(rustc, rust_code, s)
        assert actual == expected


@pytest.mark.full
def test_stringrules_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    axes = StringRulesAxes(
        n_rules=3,
        string_length_range=(0, 10),
        charset="ascii_letters_digits",
    )
    sample_inputs = (
        "",
        "a",
        "A1",
        "abc",
        "XYZ",
        "aBc123",
        "___",
    )
    for _ in range(8):
        spec = sample_stringrules_spec(axes, rng=rng)
        java_code = render_java(spec, func_name="f")
        rust_code = render_rust(spec, func_name="f")
        for s in sample_inputs:
            expected = eval_stringrules(spec, s)
            assert _run_java_f(javac, java, java_code, s) == expected
            assert _run_rust_f(rustc, rust_code, s) == expected


@pytest.mark.full
def test_stringrules_runtime_parity_non_ascii_length_cmp() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    spec = StringRulesSpec(
        rules=[
            StringRule(
                predicate=StringPredicateLengthCmp(op="eq", value=1),
                transform=StringTransformAppend(suffix="!"),
            )
        ],
        default_transform=StringTransformIdentity(),
    )
    java_code = render_java(spec, func_name="f")
    rust_code = render_rust(spec, func_name="f")

    for s in (
        "🙂",
        "é",
        "a",
        "e\u0301",
        "👨\u200d👩\u200d👧\u200d👦",
        "éβ",
        "🙂🙂",
    ):
        expected = eval_stringrules(spec, s)
        assert _run_java_f(javac, java, java_code, s) == expected
        assert _run_rust_f(rustc, rust_code, s) == expected


@pytest.mark.full
def test_stringrules_runtime_parity_non_ascii_length_cmp_eq_two() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    spec = StringRulesSpec(
        rules=[
            StringRule(
                predicate=StringPredicateLengthCmp(op="eq", value=2),
                transform=StringTransformAppend(suffix="!"),
            )
        ],
        default_transform=StringTransformIdentity(),
    )
    java_code = render_java(spec, func_name="f")
    rust_code = render_rust(spec, func_name="f")

    for s in ("e\u0301", "🙂🙂", "🇺🇳", "é", "🙂"):
        expected = eval_stringrules(spec, s)
        assert _run_java_f(javac, java, java_code, s) == expected
        assert _run_rust_f(rustc, rust_code, s) == expected
