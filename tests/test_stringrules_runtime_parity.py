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

from genfxn.core.string_predicates import (
    StringPredicateIsAlpha,
    StringPredicateIsDigit,
    StringPredicateIsLower,
    StringPredicateIsUpper,
    StringPredicateLengthCmp,
)
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
        run_checked_subprocess(
            [javac, str(src)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [java, "-cp", str(tmp), "Main"],
            cwd=tmp,
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
        run_checked_subprocess(
            [rustc, str(src), "-O", "-o", str(out)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [str(out)],
            cwd=tmp,
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


@pytest.mark.full
def test_stringrules_runtime_parity_unicode_is_alpha_non_bmp() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    spec = StringRulesSpec(
        rules=[
            StringRule(
                predicate=StringPredicateIsAlpha(),
                transform=StringTransformAppend(suffix="!"),
            )
        ],
        default_transform=StringTransformIdentity(),
    )
    java_code = render_java(spec, func_name="f")
    rust_code = render_rust(spec, func_name="f")

    for s in ("𝔘", "é", "A", "🙂"):
        expected = eval_stringrules(spec, s)
        assert _run_java_f(javac, java, java_code, s) == expected
        assert _run_rust_f(rustc, rust_code, s) == expected


@pytest.mark.full
def test_stringrules_runtime_parity_unicode_is_digit() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    spec = StringRulesSpec(
        rules=[
            StringRule(
                predicate=StringPredicateIsDigit(),
                transform=StringTransformAppend(suffix="!"),
            )
        ],
        default_transform=StringTransformIdentity(),
    )
    java_code = render_java(spec, func_name="f")
    rust_code = render_rust(spec, func_name="f")

    for s in ("𝟘", "٣", "7", "Ⅷ", "¼"):
        expected = eval_stringrules(spec, s)
        assert _run_java_f(javac, java, java_code, s) == expected
        assert _run_rust_f(rustc, rust_code, s) == expected


@pytest.mark.full
def test_stringrules_runtime_parity_uncased_scripts_for_case_predicates(
) -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    upper_spec = StringRulesSpec(
        rules=[
            StringRule(
                predicate=StringPredicateIsUpper(),
                transform=StringTransformAppend(suffix="U"),
            )
        ],
        default_transform=StringTransformIdentity(),
    )
    lower_spec = StringRulesSpec(
        rules=[
            StringRule(
                predicate=StringPredicateIsLower(),
                transform=StringTransformAppend(suffix="L"),
            )
        ],
        default_transform=StringTransformIdentity(),
    )

    upper_java = render_java(upper_spec, func_name="f")
    upper_rust = render_rust(upper_spec, func_name="f")
    lower_java = render_java(lower_spec, func_name="f")
    lower_rust = render_rust(lower_spec, func_name="f")

    for s in ("漢字", "ABC", "abc", "AbC"):
        expected_upper = eval_stringrules(upper_spec, s)
        expected_lower = eval_stringrules(lower_spec, s)
        assert _run_java_f(javac, java, upper_java, s) == expected_upper
        assert _run_rust_f(rustc, upper_rust, s) == expected_upper
        assert _run_java_f(javac, java, lower_java, s) == expected_lower
        assert _run_rust_f(rustc, lower_rust, s) == expected_lower
