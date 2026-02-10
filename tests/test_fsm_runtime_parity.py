import random
import subprocess
import tempfile
from pathlib import Path

import pytest
from helpers import (
    require_java_runtime,
    require_rust_runtime,
    run_checked_subprocess,
)

from genfxn.fsm.eval import eval_fsm
from genfxn.fsm.models import FsmAxes, FsmSpec
from genfxn.fsm.sampler import sample_fsm_spec
from genfxn.fsm.task import generate_fsm_task
from genfxn.langs.java.fsm import render_fsm as render_fsm_java
from genfxn.langs.rust.fsm import render_fsm as render_fsm_rust

_UNDEFINED_TRANSITION_ERROR = (
    "undefined transition encountered under error policy"
)


def _assert_semantic_runtime_error(
    exc: subprocess.CalledProcessError, expected_message: str
) -> None:
    combined_output = f"{exc.stdout}\n{exc.stderr}"
    assert exc.returncode != 0
    assert expected_message in combined_output


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
        "    println!(\"{}\", f(&xs));\n"
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
def test_fsm_java_runtime_parity() -> None:
    javac, java = require_java_runtime()
    task = generate_fsm_task(rng=random.Random(42))
    spec = FsmSpec.model_validate(task.spec)
    java_code = render_fsm_java(spec, func_name="f")

    for query in task.queries:
        expected = eval_fsm(spec, list(query.input))
        actual = _run_java_f(javac, java, java_code, list(query.input))
        assert actual == expected


@pytest.mark.full
def test_fsm_rust_runtime_parity() -> None:
    rustc = require_rust_runtime()
    task = generate_fsm_task(rng=random.Random(99))
    spec = FsmSpec.model_validate(task.spec)
    rust_code = render_fsm_rust(spec, func_name="f")

    for query in task.queries:
        expected = eval_fsm(spec, list(query.input))
        actual = _run_rust_f(rustc, rust_code, list(query.input))
        assert actual == expected


@pytest.mark.full
def test_fsm_runtime_parity_across_sampled_specs() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    rng = random.Random(77)
    for _ in range(8):
        spec = sample_fsm_spec(FsmAxes(), rng=rng)
        java_code = render_fsm_java(spec, func_name="f")
        rust_code = render_fsm_rust(spec, func_name="f")
        for xs in ([], [0], [1, 2], [-3, 4, 5], [7, 7, 7, 7]):
            try:
                expected = eval_fsm(spec, xs)
            except ValueError as err:
                assert str(err) == _UNDEFINED_TRANSITION_ERROR
                with pytest.raises(subprocess.CalledProcessError) as java_err:
                    _run_java_f(javac, java, java_code, xs)
                _assert_semantic_runtime_error(java_err.value, str(err))
                with pytest.raises(subprocess.CalledProcessError) as rust_err:
                    _run_rust_f(rustc, rust_code, xs)
                _assert_semantic_runtime_error(rust_err.value, str(err))
            else:
                assert _run_java_f(javac, java, java_code, xs) == expected
                assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_fsm_runtime_parity_forced_output_modes_and_policies() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    cases: tuple[tuple[FsmSpec, tuple[list[int], ...]], ...] = (
        (
            FsmSpec.model_validate(
                {
                    "machine_type": "moore",
                    "output_mode": "final_state_id",
                    "undefined_transition_policy": "stay",
                    "start_state_id": 0,
                    "states": [
                        {
                            "id": 0,
                            "is_accept": False,
                            "transitions": [
                                {
                                    "predicate": {"kind": "even"},
                                    "target_state_id": 1,
                                }
                            ],
                        },
                        {
                            "id": 1,
                            "is_accept": True,
                            "transitions": [
                                {
                                    "predicate": {"kind": "odd"},
                                    "target_state_id": 0,
                                }
                            ],
                        },
                    ],
                }
            ),
            ([2, 4, 5, 8], [4, 6]),
        ),
        (
            FsmSpec.model_validate(
                {
                    "machine_type": "moore",
                    "output_mode": "transition_count",
                    "undefined_transition_policy": "sink",
                    "start_state_id": 0,
                    "states": [
                        {"id": 0, "is_accept": False, "transitions": []}
                    ],
                }
            ),
            ([1, 2, 3], []),
        ),
        (
            FsmSpec.model_validate(
                {
                    "machine_type": "moore",
                    "output_mode": "accept_bool",
                    "undefined_transition_policy": "error",
                    "start_state_id": 0,
                    "states": [
                        {
                            "id": 0,
                            "is_accept": False,
                            "transitions": [
                                {
                                    "predicate": {
                                        "kind": "lt",
                                        "value": 0,
                                    },
                                    "target_state_id": 1,
                                }
                            ],
                        },
                        {"id": 1, "is_accept": True, "transitions": []},
                    ],
                }
            ),
            ([-1], [5]),
        ),
    )

    for spec, sample_inputs in cases:
        java_code = render_fsm_java(spec, func_name="f")
        rust_code = render_fsm_rust(spec, func_name="f")
        for xs in sample_inputs:
            try:
                expected = eval_fsm(spec, xs)
            except ValueError as err:
                assert str(err) == _UNDEFINED_TRANSITION_ERROR
                with pytest.raises(subprocess.CalledProcessError) as java_err:
                    _run_java_f(javac, java, java_code, xs)
                _assert_semantic_runtime_error(java_err.value, str(err))
                with pytest.raises(subprocess.CalledProcessError) as rust_err:
                    _run_rust_f(rustc, rust_code, xs)
                _assert_semantic_runtime_error(rust_err.value, str(err))
            else:
                assert _run_java_f(javac, java, java_code, xs) == expected
                assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_fsm_runtime_parity_lt_out_of_int32_threshold() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()
    spec = FsmSpec.model_validate(
        {
            "machine_type": "moore",
            "output_mode": "accept_bool",
            "undefined_transition_policy": "stay",
            "start_state_id": 0,
            "states": [
                {
                    "id": 0,
                    "is_accept": False,
                    "transitions": [
                        {
                            "predicate": {
                                "kind": "lt",
                                "value": 2_147_483_648,
                            },
                            "target_state_id": 1,
                        }
                    ],
                },
                {"id": 1, "is_accept": True, "transitions": []},
            ],
        }
    )
    java_code = render_fsm_java(spec, func_name="f")
    rust_code = render_fsm_rust(spec, func_name="f")

    for xs in ([2_147_483_647], [0], [-2_147_483_648], []):
        expected = eval_fsm(spec, xs)
        assert _run_java_f(javac, java, java_code, xs) == expected
        assert _run_rust_f(rustc, rust_code, xs) == expected
