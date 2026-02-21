import random

from genfxn.core.trace import TraceStep, trace_step
from genfxn.stack_bytecode.models import (
    InputMode,
    Instruction,
    InstructionOp,
    JumpTargetMode,
    StackBytecodeAxes,
    StackBytecodeSpec,
)

_PROGRAM_LENGTH_RANGE = (2, 12)
_OP_CHOICES = [
    InstructionOp.PUSH_CONST,
    InstructionOp.LOAD_INPUT,
    InstructionOp.DUP,
    InstructionOp.SWAP,
    InstructionOp.POP,
    InstructionOp.ADD,
    InstructionOp.SUB,
    InstructionOp.MUL,
    InstructionOp.DIV,
    InstructionOp.MOD,
    InstructionOp.NEG,
    InstructionOp.ABS,
    InstructionOp.EQ,
    InstructionOp.GT,
    InstructionOp.LT,
    InstructionOp.IS_ZERO,
    InstructionOp.JUMP,
    InstructionOp.JUMP_IF_ZERO,
    InstructionOp.JUMP_IF_NONZERO,
    InstructionOp.HALT,
]


def _sample_instruction(
    axes: StackBytecodeAxes,
    program_len: int,
    instruction_index: int,
    rng: random.Random,
) -> Instruction:
    op = rng.choice(_OP_CHOICES)
    if op == InstructionOp.HALT:
        # Keep halts in the weighted pool, but reserve terminal halt position.
        op = InstructionOp.PUSH_CONST

    if op == InstructionOp.PUSH_CONST:
        lo, hi = axes.const_range
        return Instruction(op=op, value=rng.randint(lo, hi))
    if op == InstructionOp.LOAD_INPUT:
        _, idx_hi = axes.list_length_range
        span = max(1, idx_hi + 2)
        return Instruction(op=op, index=rng.randint(-span, span))
    if op in (
        InstructionOp.JUMP,
        InstructionOp.JUMP_IF_ZERO,
        InstructionOp.JUMP_IF_NONZERO,
    ):
        if instruction_index > 0 and rng.random() < 0.4:
            return Instruction(
                op=op, target=rng.randint(0, instruction_index - 1)
            )
        return Instruction(op=op, target=rng.randint(-program_len, program_len))
    return Instruction(op=op)


def _inject_control_flow(
    program: list[Instruction], rng: random.Random
) -> None:
    if len(program) <= 3:
        return
    if rng.random() < 0.5:
        first_idx = rng.randint(1, len(program) - 2)
        program[first_idx] = Instruction(
            op=rng.choice(
                [InstructionOp.JUMP_IF_ZERO, InstructionOp.JUMP_IF_NONZERO]
            ),
            target=rng.randint(0, first_idx - 1),
        )
    if len(program) <= 5 or rng.random() < 0.65:
        return
    candidate_indices = [idx for idx in range(2, len(program) - 1)]
    if not candidate_indices:
        return
    second_idx = rng.choice(candidate_indices)
    program[second_idx] = Instruction(
        op=InstructionOp.JUMP,
        target=rng.randint(0, second_idx - 1),
    )


def sample_stack_bytecode_spec(
    axes: StackBytecodeAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> StackBytecodeSpec:
    if rng is None:
        rng = random.Random()

    len_lo, len_hi = axes.list_length_range
    if len_lo > len_hi:
        raise ValueError(
            f"list_length_range: low ({len_lo}) must be <= high ({len_hi})"
        )

    step_lo, step_hi = axes.max_step_count_range
    if step_lo > step_hi:
        raise ValueError(
            f"max_step_count_range: low ({step_lo}) must be <= high ({step_hi})"
        )

    n_program = rng.randint(*_PROGRAM_LENGTH_RANGE)
    trace_step(
        trace,
        "sample_program_length",
        f"Program length: {n_program}",
        n_program,
    )

    program = [
        _sample_instruction(
            axes=axes,
            program_len=n_program,
            instruction_index=idx,
            rng=rng,
        )
        for idx in range(n_program - 1)
    ]
    program.append(Instruction(op=InstructionOp.HALT))
    _inject_control_flow(program, rng)

    jump_mode = rng.choice(axes.jump_target_modes)
    input_mode = rng.choice(axes.input_modes)
    max_steps = rng.randint(step_lo, step_hi)

    trace_step(
        trace,
        "sample_runtime_modes",
        (
            "Modes: jump_target_mode="
            f"{jump_mode.value}, input_mode={input_mode.value}, "
            f"max_step_count={max_steps}"
        ),
        {
            "jump_target_mode": jump_mode.value,
            "input_mode": input_mode.value,
            "max_step_count": max_steps,
        },
    )
    trace_step(
        trace,
        "sample_program",
        "Sampled program instructions",
        [instr.model_dump() for instr in program],
    )

    return StackBytecodeSpec(
        program=program,
        max_step_count=max_steps,
        jump_target_mode=JumpTargetMode(jump_mode),
        input_mode=InputMode(input_mode),
    )
