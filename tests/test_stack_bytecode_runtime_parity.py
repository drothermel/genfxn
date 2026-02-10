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
from genfxn.stack_bytecode.models import (
    InputMode,
    Instruction,
    InstructionOp,
    JumpTargetMode,
    StackBytecodeAxes,
    StackBytecodeSpec,
)
from genfxn.stack_bytecode.sampler import sample_stack_bytecode_spec
from genfxn.stack_bytecode.task import generate_stack_bytecode_task


def _is_int_not_bool(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _long_literal(value: int) -> str:
    if value == -(1 << 63):
        return "Long.MIN_VALUE"
    return f"{value}L"


def _i64_literal(value: int) -> str:
    if value == -(1 << 63):
        return "i64::MIN"
    return f"{value}i64"


def _i64_wrap(value: int) -> int:
    wrapped = value & ((1 << 64) - 1)
    if wrapped >= (1 << 63):
        return wrapped - (1 << 64)
    return wrapped


def _runtime_output_from_eval(eval_out: tuple[int, int]) -> tuple[int, int]:
    status, value = eval_out
    return int(status), _i64_wrap(value)


def _parse_query_input(input_value: Any) -> list[int]:
    if not isinstance(input_value, list):
        raise TypeError("stack_bytecode query input must be list[int]")
    if not all(_is_int_not_bool(v) for v in input_value):
        raise TypeError("stack_bytecode query input must be list[int]")
    return [int(v) for v in input_value]


def _run_java_f(
    javac: str, java: str, code: str, xs: list[int]
) -> tuple[int, int]:
    xs_lit = ", ".join(_long_literal(x) for x in xs)
    main_src = (
        "public class Main {\n"
        f"{code}\n"
        "  public static void main(String[] args) {\n"
        f"    long[] xs = new long[]{{{xs_lit}}};\n"
        "    long[] out = f(xs);\n"
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


def _run_rust_f(
    rustc: str,
    code: str,
    xs: list[int],
    *,
    optimize: bool = True,
) -> tuple[int, int]:
    xs_lit = ", ".join(_i64_literal(x) for x in xs)
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
        compile_cmd = [rustc, str(src)]
        if optimize:
            compile_cmd.append("-O")
        compile_cmd.extend(["-o", str(out)])
        subprocess.run(  # noqa: S603
            compile_cmd,
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


@pytest.mark.full
def test_stack_bytecode_runtime_parity_forced_modes_and_statuses() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    cases: tuple[tuple[StackBytecodeSpec, list[int]], ...] = (
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.PUSH_CONST, value=7),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=4,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.JUMP, target=0),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=3,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.POP),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=4,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.JUMP, target=99),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=4,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.PUSH_CONST, value=1),
                    Instruction(op=InstructionOp.PUSH_CONST, value=0),
                    Instruction(op=InstructionOp.DIV),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=8,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.LOAD_INPUT, index=2),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=4,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[Instruction(op=InstructionOp.HALT)],
                max_step_count=2,
                jump_target_mode=JumpTargetMode.ERROR,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.JUMP, target=99),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=3,
                jump_target_mode=JumpTargetMode.CLAMP,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
        (
            StackBytecodeSpec(
                program=[
                    Instruction(op=InstructionOp.JUMP, target=-1),
                    Instruction(op=InstructionOp.HALT),
                ],
                max_step_count=3,
                jump_target_mode=JumpTargetMode.WRAP,
                input_mode=InputMode.DIRECT,
            ),
            [],
        ),
    )

    for spec, xs in cases:
        java_code = render_stack_bytecode_java(spec, func_name="f")
        rust_code = render_stack_bytecode_rust(spec, func_name="f")
        expected = eval_stack_bytecode(spec, xs)
        assert _run_java_f(javac, java, java_code, xs) == expected
        assert _run_rust_f(rustc, rust_code, xs) == expected


@pytest.mark.full
def test_stack_bytecode_runtime_parity_overflow_adjacent_cases() -> None:
    javac, java = require_java_runtime()
    rustc = require_rust_runtime()

    max_i64 = (1 << 63) - 1
    min_i64 = -(1 << 63)

    cases: tuple[StackBytecodeSpec, ...] = (
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=max_i64),
                Instruction(op=InstructionOp.PUSH_CONST, value=1),
                Instruction(op=InstructionOp.ADD),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=8,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=min_i64),
                Instruction(op=InstructionOp.PUSH_CONST, value=1),
                Instruction(op=InstructionOp.SUB),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=8,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=max_i64),
                Instruction(op=InstructionOp.PUSH_CONST, value=2),
                Instruction(op=InstructionOp.MUL),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=8,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=min_i64),
                Instruction(op=InstructionOp.NEG),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=6,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=min_i64),
                Instruction(op=InstructionOp.ABS),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=6,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=min_i64),
                Instruction(op=InstructionOp.PUSH_CONST, value=-1),
                Instruction(op=InstructionOp.DIV),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=8,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
        StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=min_i64),
                Instruction(op=InstructionOp.PUSH_CONST, value=-1),
                Instruction(op=InstructionOp.MOD),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=8,
            jump_target_mode=JumpTargetMode.ERROR,
            input_mode=InputMode.DIRECT,
        ),
    )

    for spec in cases:
        expected = _runtime_output_from_eval(eval_stack_bytecode(spec, []))
        java_code = render_stack_bytecode_java(spec, func_name="f")
        rust_code = render_stack_bytecode_rust(spec, func_name="f")
        assert _run_java_f(javac, java, java_code, []) == expected
        assert _run_rust_f(rustc, rust_code, [], optimize=False) == expected
        assert _run_rust_f(rustc, rust_code, [], optimize=True) == expected
