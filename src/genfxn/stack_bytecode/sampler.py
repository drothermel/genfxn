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

_NULLARY_OPS = [
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
]


def _sample_instruction(
    axes: StackBytecodeAxes,
    program_len: int,
    rng: random.Random,
) -> Instruction:
    op_choices = [
        InstructionOp.PUSH_CONST,
        InstructionOp.LOAD_INPUT,
        InstructionOp.JUMP,
        InstructionOp.JUMP_IF_ZERO,
        InstructionOp.JUMP_IF_NONZERO,
    ] + _NULLARY_OPS
    op = rng.choice(op_choices)

    if op == InstructionOp.PUSH_CONST:
        lo, hi = axes.const_range
        return Instruction(op=op, value=rng.randint(lo, hi))
    if op == InstructionOp.LOAD_INPUT:
        _, idx_hi = axes.list_length_range
        span = max(1, idx_hi + 2)
        # Include negatives and slightly out-of-range indices.
        return Instruction(op=op, index=rng.randint(-span, span))
    if op in (
        InstructionOp.JUMP,
        InstructionOp.JUMP_IF_ZERO,
        InstructionOp.JUMP_IF_NONZERO,
    ):
        return Instruction(op=op, target=rng.randint(-program_len, program_len))
    return Instruction(op=op)


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

    n_program = rng.randint(2, 12)
    trace_step(
        trace,
        "sample_program_length",
        f"Program length: {n_program}",
        n_program,
    )

    program = [
        _sample_instruction(axes, n_program, rng) for _ in range(n_program - 1)
    ]
    program.append(Instruction(op=InstructionOp.HALT))

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
