import inspect
import random
from typing import Any

import pytest

from genfxn.stack_bytecode.models import (
    InputMode,
    Instruction,
    InstructionOp,
    JumpTargetMode,
    RuntimeStatus,
    StackBytecodeAxes,
    StackBytecodeSpec,
)


def _import_optional(module_path: str):
    return pytest.importorskip(module_path)


def _get_callable(module: Any, *names: str):
    for name in names:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    pytest.skip(f"No callable found in {module.__name__}: {names}")


def _call_eval(eval_fn: Any, spec: Any, xs: list[int]) -> Any:
    attempts = [
        lambda: eval_fn(spec, xs),
        lambda: eval_fn(spec=spec, xs=xs),
        lambda: eval_fn(spec=spec, inputs=xs),
        lambda: eval_fn(program=spec, xs=xs),
        lambda: eval_fn(program=spec, inputs=xs),
    ]
    for attempt in attempts:
        try:
            return attempt()
        except TypeError:
            continue
    sig = inspect.signature(eval_fn)
    raise AssertionError(f"Could not call evaluator with signature {sig}")


def _result_output_and_status(result: Any) -> tuple[int, Any | None]:
    if isinstance(result, int):
        return result, None

    if isinstance(result, tuple):
        if len(result) >= 2 and all(isinstance(x, int) for x in result[:2]):
            # stack_bytecode returns (status, value)
            return result[1], result[0]

    for out_name in ("output", "value", "result", "top"):
        out = getattr(result, out_name, None)
        if isinstance(out, int):
            status = getattr(result, "status", None)
            if status is None:
                status = getattr(result, "runtime_status", None)
            return out, status

    raise AssertionError(
        f"Unsupported evaluator result shape: {type(result)!r}"
    )


def _call_sample(sample_fn: Any, axes: StackBytecodeAxes, rng: random.Random):
    try:
        return sample_fn(axes, rng)
    except TypeError:
        return sample_fn(axes=axes, rng=rng)


def _call_generate_queries(
    queries_fn: Any,
    spec: StackBytecodeSpec,
    axes: StackBytecodeAxes,
    rng: random.Random,
):
    try:
        return queries_fn(spec, axes, rng)
    except TypeError:
        return queries_fn(spec=spec, axes=axes, rng=rng)


class TestModels:
    def test_instruction_requires_value_for_push_const(self) -> None:
        with pytest.raises(ValueError, match="requires field 'value'"):
            Instruction(op=InstructionOp.PUSH_CONST)

    def test_instruction_requires_index_for_load_input(self) -> None:
        with pytest.raises(ValueError, match="requires field 'index'"):
            Instruction(op=InstructionOp.LOAD_INPUT)

    def test_instruction_requires_target_for_jumps(self) -> None:
        with pytest.raises(ValueError, match="requires field 'target'"):
            Instruction(op=InstructionOp.JUMP)

    def test_spec_requires_halt_instruction(self) -> None:
        with pytest.raises(ValueError, match="halt"):
            StackBytecodeSpec(
                program=[Instruction(op=InstructionOp.PUSH_CONST, value=1)]
            )

    def test_axes_validate_ranges(self) -> None:
        with pytest.raises(ValueError, match="value_range"):
            StackBytecodeAxes(value_range=(2, -2))

    def test_axes_reject_empty_modes(self) -> None:
        with pytest.raises(ValueError, match="jump_target_modes"):
            StackBytecodeAxes(jump_target_modes=[])

    def test_axes_reject_negative_list_length_low(self) -> None:
        with pytest.raises(ValueError, match="list_length_range"):
            StackBytecodeAxes(list_length_range=(-1, 3))


class TestEvaluatorSemantics:
    def test_arithmetic_program(self) -> None:
        eval_module = _import_optional("genfxn.stack_bytecode.eval")
        eval_fn = _get_callable(
            eval_module,
            "eval_stack_bytecode",
            "eval_program",
            "eval_stack_program",
        )

        spec = StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=3),
                Instruction(op=InstructionOp.PUSH_CONST, value=4),
                Instruction(op=InstructionOp.MUL),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        result = _call_eval(eval_fn, spec, [])
        output, status = _result_output_and_status(result)

        assert output == 12
        if status is not None:
            assert status in (RuntimeStatus.OK, int(RuntimeStatus.OK), "ok")

    def test_input_and_unary_ops(self) -> None:
        eval_module = _import_optional("genfxn.stack_bytecode.eval")
        eval_fn = _get_callable(
            eval_module,
            "eval_stack_bytecode",
            "eval_program",
            "eval_stack_program",
        )

        spec = StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.LOAD_INPUT, index=0),
                Instruction(op=InstructionOp.DUP),
                Instruction(op=InstructionOp.MUL),
                Instruction(op=InstructionOp.NEG),
                Instruction(op=InstructionOp.ABS),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        result = _call_eval(eval_fn, spec, [7])
        output, _ = _result_output_and_status(result)
        assert output == 49


class TestSamplerAndQueries:
    def test_sampler_reproducible(self) -> None:
        sampler_module = _import_optional("genfxn.stack_bytecode.sampler")
        sample_fn = _get_callable(
            sampler_module,
            "sample_stack_bytecode_spec",
            "sample_spec",
        )
        axes = StackBytecodeAxes(target_difficulty=3)

        spec1 = _call_sample(sample_fn, axes, random.Random(42))
        spec2 = _call_sample(sample_fn, axes, random.Random(42))
        assert spec1 == spec2

    def test_queries_match_evaluator_outputs(self) -> None:
        sampler_module = _import_optional("genfxn.stack_bytecode.sampler")
        queries_module = _import_optional("genfxn.stack_bytecode.queries")
        eval_module = _import_optional("genfxn.stack_bytecode.eval")

        sample_fn = _get_callable(
            sampler_module,
            "sample_stack_bytecode_spec",
            "sample_spec",
        )
        queries_fn = _get_callable(
            queries_module,
            "generate_stack_bytecode_queries",
            "generate_queries",
        )
        eval_fn = _get_callable(
            eval_module,
            "eval_stack_bytecode",
            "eval_program",
            "eval_stack_program",
        )

        axes = StackBytecodeAxes(
            target_difficulty=2,
            list_length_range=(0, 5),
            input_modes=[InputMode.DIRECT, InputMode.CYCLIC],
            jump_target_modes=[
                JumpTargetMode.ERROR,
                JumpTargetMode.CLAMP,
                JumpTargetMode.WRAP,
            ],
        )

        spec = _call_sample(sample_fn, axes, random.Random(42))
        queries = _call_generate_queries(
            queries_fn,
            spec,
            axes,
            random.Random(42),
        )

        assert len(queries) > 0
        for q in queries:
            assert q.output == _call_eval(eval_fn, spec, list(q.input))


class TestRenderRoundtrip:
    def test_python_render_executes_and_matches_eval(self) -> None:
        render_module = _import_optional("genfxn.stack_bytecode.render")
        eval_module = _import_optional("genfxn.stack_bytecode.eval")

        render_fn = _get_callable(
            render_module,
            "render_stack_bytecode",
            "render_program",
        )
        eval_fn = _get_callable(
            eval_module,
            "eval_stack_bytecode",
            "eval_program",
            "eval_stack_program",
        )

        spec = StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.LOAD_INPUT, index=0),
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.ADD),
                Instruction(op=InstructionOp.HALT),
            ]
        )

        code = render_fn(spec)
        namespace: dict[str, Any] = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]

        for xs in ([], [0], [7], [-3]):
            rendered_out = f(xs)
            eval_out = _call_eval(eval_fn, spec, xs)
            assert rendered_out == eval_out


class TestTaskGeneration:
    def test_generate_task_reproducible_with_seed(self) -> None:
        task_module = _import_optional("genfxn.stack_bytecode.task")
        generate_fn = _get_callable(
            task_module,
            "generate_stack_bytecode_task",
            "generate_task",
        )

        task1 = generate_fn(rng=random.Random(42))
        task2 = generate_fn(rng=random.Random(42))

        assert task1.task_id == task2.task_id
        assert task1.spec == task2.spec
        assert task1.queries == task2.queries
