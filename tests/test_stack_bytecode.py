import random

import pytest

from genfxn.core.models import QueryTag
from genfxn.stack_bytecode.eval import eval_stack_bytecode
from genfxn.stack_bytecode.models import (
    InputMode,
    Instruction,
    InstructionOp,
    JumpTargetMode,
    RuntimeStatus,
    StackBytecodeAxes,
    StackBytecodeSpec,
)
from genfxn.stack_bytecode.queries import generate_stack_bytecode_queries
from genfxn.stack_bytecode.render import render_stack_bytecode
from genfxn.stack_bytecode.sampler import sample_stack_bytecode_spec
from genfxn.stack_bytecode.task import generate_stack_bytecode_task


def _spec(
    program: list[Instruction],
    *,
    max_step_count: int = 64,
    jump_target_mode: JumpTargetMode = JumpTargetMode.ERROR,
    input_mode: InputMode = InputMode.DIRECT,
) -> StackBytecodeSpec:
    return StackBytecodeSpec(
        program=program,
        max_step_count=max_step_count,
        jump_target_mode=jump_target_mode,
        input_mode=input_mode,
    )


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
            _spec([Instruction(op=InstructionOp.PUSH_CONST, value=1)])

    def test_axes_validate_ranges(self) -> None:
        with pytest.raises(ValueError, match="value_range"):
            StackBytecodeAxes(value_range=(2, -2))


class TestEvaluatorArithmeticAndComparison:
    def test_add_sub_mul_pipeline(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=9),
                Instruction(op=InstructionOp.PUSH_CONST, value=4),
                Instruction(op=InstructionOp.SUB),
                Instruction(op=InstructionOp.PUSH_CONST, value=3),
                Instruction(op=InstructionOp.MUL),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, 15)

    def test_sub_operand_order(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=2),
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.SUB),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, -3)

    @pytest.mark.parametrize(
        "a,b,expected",
        [(-7, 3, -2), (7, -3, -2), (-7, -3, 2), (7, 3, 2)],
    )
    def test_division_truncates_toward_zero(
        self, a: int, b: int, expected: int
    ) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=a),
                Instruction(op=InstructionOp.PUSH_CONST, value=b),
                Instruction(op=InstructionOp.DIV),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, expected)

    @pytest.mark.parametrize(
        "a,b,expected",
        [(-7, 3, -1), (7, -3, 1), (-7, -3, -1), (7, 3, 1)],
    )
    def test_modulo_matches_trunc_zero_division(
        self, a: int, b: int, expected: int
    ) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=a),
                Instruction(op=InstructionOp.PUSH_CONST, value=b),
                Instruction(op=InstructionOp.MOD),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, expected)

    def test_div_by_zero_returns_status(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=7),
                Instruction(op=InstructionOp.PUSH_CONST, value=0),
                Instruction(op=InstructionOp.DIV),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.DIV_OR_MOD_BY_ZERO,
            0,
        )

    def test_mod_by_zero_returns_status(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=7),
                Instruction(op=InstructionOp.PUSH_CONST, value=0),
                Instruction(op=InstructionOp.MOD),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.DIV_OR_MOD_BY_ZERO,
            0,
        )

    def test_comparison_ops(self) -> None:
        spec_eq = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.EQ),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec_eq, []) == (RuntimeStatus.OK, 1)

        spec_gt = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.PUSH_CONST, value=2),
                Instruction(op=InstructionOp.GT),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec_gt, []) == (RuntimeStatus.OK, 1)

        spec_lt = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.PUSH_CONST, value=2),
                Instruction(op=InstructionOp.LT),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec_lt, []) == (RuntimeStatus.OK, 0)


class TestEvaluatorStackOpsAndFaults:
    def test_dup_swap_pop(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=3),
                Instruction(op=InstructionOp.PUSH_CONST, value=8),
                Instruction(op=InstructionOp.SWAP),
                Instruction(op=InstructionOp.DUP),
                Instruction(op=InstructionOp.POP),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, 3)

    @pytest.mark.parametrize(
        "op",
        [
            InstructionOp.DUP,
            InstructionOp.POP,
            InstructionOp.NEG,
            InstructionOp.ABS,
            InstructionOp.IS_ZERO,
            InstructionOp.JUMP_IF_ZERO,
            InstructionOp.JUMP_IF_NONZERO,
        ],
    )
    def test_single_operand_underflow_returns_status(
        self, op: InstructionOp
    ) -> None:
        if "jump_if" in op.value:
            instr = Instruction(op=op, target=0)
        else:
            instr = Instruction(op=op)
        spec = _spec([instr, Instruction(op=InstructionOp.HALT)])
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.STACK_UNDERFLOW,
            0,
        )

    @pytest.mark.parametrize(
        "op",
        [
            InstructionOp.SWAP,
            InstructionOp.ADD,
            InstructionOp.SUB,
            InstructionOp.MUL,
            InstructionOp.DIV,
            InstructionOp.MOD,
            InstructionOp.EQ,
            InstructionOp.GT,
            InstructionOp.LT,
        ],
    )
    def test_two_operand_underflow_returns_status(
        self, op: InstructionOp
    ) -> None:
        spec = _spec([Instruction(op=op), Instruction(op=InstructionOp.HALT)])
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.STACK_UNDERFLOW,
            0,
        )

    def test_halt_with_empty_stack_returns_status(self) -> None:
        spec = _spec([Instruction(op=InstructionOp.HALT)])
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.EMPTY_STACK_ON_HALT,
            0,
        )


class TestEvaluatorControlFlow:
    def test_jump_error_mode_invalid_target(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.JUMP, target=10),
                Instruction(op=InstructionOp.HALT),
            ],
            jump_target_mode=JumpTargetMode.ERROR,
        )
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.BAD_JUMP_TARGET,
            0,
        )

    def test_jump_clamp_mode(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=4),
                Instruction(op=InstructionOp.JUMP, target=10),
                Instruction(op=InstructionOp.HALT),
            ],
            jump_target_mode=JumpTargetMode.CLAMP,
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, 4)

    def test_jump_wrap_mode(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.JUMP, target=6),
                Instruction(op=InstructionOp.PUSH_CONST, value=0),
                Instruction(op=InstructionOp.PUSH_CONST, value=9),
                Instruction(op=InstructionOp.HALT),
            ],
            jump_target_mode=JumpTargetMode.WRAP,
            max_step_count=8,
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, 9)

    def test_conditional_jumps_consume_condition_value(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=0),
                Instruction(op=InstructionOp.JUMP_IF_ZERO, target=4),
                Instruction(op=InstructionOp.PUSH_CONST, value=100),
                Instruction(op=InstructionOp.JUMP, target=5),
                Instruction(op=InstructionOp.PUSH_CONST, value=7),
                Instruction(op=InstructionOp.HALT),
            ],
            jump_target_mode=JumpTargetMode.ERROR,
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.OK, 7)

    def test_step_limit(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.PUSH_CONST, value=1),
                Instruction(op=InstructionOp.JUMP, target=0),
                Instruction(op=InstructionOp.HALT),
            ],
            max_step_count=5,
            jump_target_mode=JumpTargetMode.ERROR,
        )
        assert eval_stack_bytecode(spec, []) == (RuntimeStatus.STEP_LIMIT, 0)


class TestInputModes:
    def test_load_input_direct_valid(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.LOAD_INPUT, index=1),
                Instruction(op=InstructionOp.HALT),
            ],
            input_mode=InputMode.DIRECT,
        )
        assert eval_stack_bytecode(spec, [10, 20, 30]) == (RuntimeStatus.OK, 20)

    def test_load_input_direct_invalid_index(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.LOAD_INPUT, index=-1),
                Instruction(op=InstructionOp.HALT),
            ],
            input_mode=InputMode.DIRECT,
        )
        assert eval_stack_bytecode(spec, [10]) == (
            RuntimeStatus.INVALID_INPUT_INDEX,
            0,
        )

    def test_load_input_cyclic_wraps(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.LOAD_INPUT, index=5),
                Instruction(op=InstructionOp.HALT),
            ],
            input_mode=InputMode.CYCLIC,
        )
        assert eval_stack_bytecode(spec, [11, 22]) == (RuntimeStatus.OK, 22)

    def test_load_input_cyclic_empty(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.LOAD_INPUT, index=5),
                Instruction(op=InstructionOp.HALT),
            ],
            input_mode=InputMode.CYCLIC,
        )
        assert eval_stack_bytecode(spec, []) == (
            RuntimeStatus.INVALID_INPUT_INDEX,
            0,
        )


class TestSamplerAndQueries:
    def test_sampler_reproducible(self) -> None:
        axes = StackBytecodeAxes(target_difficulty=3)
        spec1 = sample_stack_bytecode_spec(axes, random.Random(42))
        spec2 = sample_stack_bytecode_spec(axes, random.Random(42))
        assert spec1 == spec2

    def test_sampler_always_emits_halt(self) -> None:
        axes = StackBytecodeAxes(target_difficulty=3)
        spec = sample_stack_bytecode_spec(axes, random.Random(42))
        assert any(instr.op == InstructionOp.HALT for instr in spec.program)

    def test_queries_match_evaluator_outputs(self) -> None:
        axes = StackBytecodeAxes(target_difficulty=2, list_length_range=(0, 5))
        spec = sample_stack_bytecode_spec(axes, random.Random(42))
        queries = generate_stack_bytecode_queries(spec, axes, random.Random(42))

        assert len(queries) > 0
        assert {q.tag for q in queries}.issubset(set(QueryTag))
        for q in queries:
            assert q.output == eval_stack_bytecode(spec, list(q.input))


class TestRenderRoundtrip:
    def test_python_render_executes_and_matches_eval(self) -> None:
        spec = _spec(
            [
                Instruction(op=InstructionOp.LOAD_INPUT, index=0),
                Instruction(op=InstructionOp.PUSH_CONST, value=5),
                Instruction(op=InstructionOp.ADD),
                Instruction(op=InstructionOp.HALT),
            ]
        )

        code = render_stack_bytecode(spec)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        assert callable(f)

        for xs in ([], [0], [7], [-3]):
            rendered_out = f(xs)
            eval_out = eval_stack_bytecode(spec, xs)
            assert rendered_out == eval_out


class TestTaskGeneration:
    def test_generate_task_reproducible_with_seed(self) -> None:
        task1 = generate_stack_bytecode_task(rng=random.Random(42))
        task2 = generate_stack_bytecode_task(rng=random.Random(42))

        assert task1.task_id == task2.task_id
        assert task1.spec == task2.spec
        assert task1.queries == task2.queries

    def test_generate_task_has_description_and_difficulty(self) -> None:
        task = generate_stack_bytecode_task(rng=random.Random(42))
        assert isinstance(task.description, str)
        assert task.description
        assert task.difficulty in {1, 2, 3, 4, 5}


class TestDifferentialProperty:
    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_rendered_python_matches_evaluator_across_random_specs(
        self, difficulty: int
    ) -> None:
        rng = random.Random(1000 + difficulty)
        axes = StackBytecodeAxes(
            target_difficulty=difficulty,
            list_length_range=(0, 8),
            value_range=(-20, 20),
        )

        for _ in range(12):
            spec = sample_stack_bytecode_spec(axes, rng)
            code = render_stack_bytecode(spec)
            namespace: dict[str, object] = {}
            exec(code, namespace)  # noqa: S102
            f = namespace["f"]
            assert callable(f)

            for _ in range(8):
                length = rng.randint(
                    axes.list_length_range[0],
                    axes.list_length_range[1],
                )
                xs = [
                    rng.randint(axes.value_range[0], axes.value_range[1])
                    for _ in range(length)
                ]
                assert f(xs) == eval_stack_bytecode(spec, xs)
