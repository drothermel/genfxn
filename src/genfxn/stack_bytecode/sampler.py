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

_TARGET_PROGRAM_LENGTH: dict[int, tuple[int, int]] = {
    1: (2, 3),
    2: (4, 5),
    3: (6, 7),
    4: (8, 10),
    5: (11, 12),
}

_TARGET_MAX_STEPS: dict[int, tuple[int, int]] = {
    1: (20, 32),
    2: (32, 64),
    3: (64, 96),
    4: (96, 128),
    5: (128, 160),
}

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


def _ops_for_target(target_difficulty: int | None) -> list[InstructionOp]:
    if target_difficulty is None:
        return [
            InstructionOp.PUSH_CONST,
            InstructionOp.LOAD_INPUT,
            InstructionOp.JUMP,
            InstructionOp.JUMP_IF_ZERO,
            InstructionOp.JUMP_IF_NONZERO,
            *_NULLARY_OPS,
        ]
    if target_difficulty <= 1:
        return [
            InstructionOp.PUSH_CONST,
            InstructionOp.LOAD_INPUT,
            InstructionOp.ADD,
            InstructionOp.SUB,
            InstructionOp.NEG,
            InstructionOp.HALT,
        ]
    if target_difficulty == 2:
        return [
            InstructionOp.PUSH_CONST,
            InstructionOp.LOAD_INPUT,
            InstructionOp.DUP,
            InstructionOp.POP,
            InstructionOp.ADD,
            InstructionOp.SUB,
            InstructionOp.MUL,
            InstructionOp.NEG,
            InstructionOp.ABS,
            InstructionOp.IS_ZERO,
            InstructionOp.HALT,
        ]
    if target_difficulty == 3:
        return [
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
            InstructionOp.HALT,
        ]
    return [
        InstructionOp.PUSH_CONST,
        InstructionOp.LOAD_INPUT,
        InstructionOp.JUMP,
        InstructionOp.JUMP_IF_ZERO,
        InstructionOp.JUMP_IF_NONZERO,
        *_NULLARY_OPS,
        InstructionOp.HALT,
    ]


def _sample_program_length(
    target_difficulty: int | None,
    rng: random.Random,
) -> int:
    if target_difficulty is None:
        return rng.randint(2, 12)
    lo, hi = _TARGET_PROGRAM_LENGTH[target_difficulty]
    return rng.randint(lo, hi)


def _intersect_ranges(
    a: tuple[int, int],
    b: tuple[int, int],
) -> tuple[int, int] | None:
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if lo > hi:
        return None
    return (lo, hi)


def _pick_max_steps(
    target_difficulty: int | None,
    axes_range: tuple[int, int],
    rng: random.Random,
) -> int:
    if target_difficulty is None:
        return rng.randint(*axes_range)
    desired = _TARGET_MAX_STEPS[target_difficulty]
    bounded = _intersect_ranges(desired, axes_range)
    if bounded is None:
        return rng.randint(*axes_range)
    return rng.randint(*bounded)


def _pick_mode_with_preference[T](
    available: list[T],
    preferred: list[T],
    rng: random.Random,
) -> T:
    preferred_available = [mode for mode in preferred if mode in available]
    if preferred_available:
        return rng.choice(preferred_available)
    return rng.choice(available)


def _sample_instruction(
    axes: StackBytecodeAxes,
    program_len: int,
    op_choices: list[InstructionOp],
    instruction_index: int,
    target_difficulty: int | None,
    rng: random.Random,
) -> Instruction:
    op = rng.choice(op_choices)
    if op == InstructionOp.HALT:
        op = InstructionOp.PUSH_CONST

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
        if (
            target_difficulty is not None
            and target_difficulty >= 4
            and instruction_index > 0
            and rng.random() < 0.7
        ):
            return Instruction(
                op=op,
                target=rng.randint(0, instruction_index - 1),
            )
        return Instruction(op=op, target=rng.randint(-program_len, program_len))
    return Instruction(op=op)


def _inject_control_flow_for_target(
    program: list[Instruction],
    target_difficulty: int | None,
    rng: random.Random,
) -> None:
    if target_difficulty is None or target_difficulty < 4:
        return
    if len(program) <= 3:
        return

    first_idx = rng.randint(1, len(program) - 2)
    program[first_idx] = Instruction(
        op=rng.choice(
            [InstructionOp.JUMP_IF_ZERO, InstructionOp.JUMP_IF_NONZERO]
        ),
        target=rng.randint(0, first_idx - 1),
    )

    if target_difficulty < 5 or len(program) <= 5:
        return

    candidate_indices = [
        idx
        for idx in range(first_idx + 1, len(program) - 1)
        if idx > 1
    ]
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

    target_difficulty = axes.target_difficulty
    n_program = _sample_program_length(target_difficulty, rng)
    trace_step(
        trace,
        "sample_program_length",
        f"Program length: {n_program}",
        n_program,
    )

    op_choices = _ops_for_target(target_difficulty)
    program = [
        _sample_instruction(
            axes=axes,
            program_len=n_program,
            op_choices=op_choices,
            instruction_index=idx,
            target_difficulty=target_difficulty,
            rng=rng,
        )
        for idx in range(n_program - 1)
    ]
    program.append(Instruction(op=InstructionOp.HALT))
    _inject_control_flow_for_target(program, target_difficulty, rng)

    if target_difficulty in {1, 2}:
        jump_mode = _pick_mode_with_preference(
            axes.jump_target_modes,
            [JumpTargetMode.ERROR],
            rng,
        )
        input_mode = _pick_mode_with_preference(
            axes.input_modes,
            [InputMode.DIRECT],
            rng,
        )
    elif target_difficulty == 3:
        jump_mode = _pick_mode_with_preference(
            axes.jump_target_modes,
            [JumpTargetMode.ERROR, JumpTargetMode.CLAMP],
            rng,
        )
        input_mode = _pick_mode_with_preference(
            axes.input_modes,
            [InputMode.DIRECT, InputMode.CYCLIC],
            rng,
        )
    elif target_difficulty == 4:
        jump_mode = _pick_mode_with_preference(
            axes.jump_target_modes,
            [JumpTargetMode.CLAMP, JumpTargetMode.WRAP],
            rng,
        )
        input_mode = _pick_mode_with_preference(
            axes.input_modes,
            [InputMode.CYCLIC, InputMode.DIRECT],
            rng,
        )
    elif target_difficulty == 5:
        jump_mode = _pick_mode_with_preference(
            axes.jump_target_modes,
            [JumpTargetMode.WRAP],
            rng,
        )
        input_mode = _pick_mode_with_preference(
            axes.input_modes,
            [InputMode.CYCLIC],
            rng,
        )
    else:
        jump_mode = rng.choice(axes.jump_target_modes)
        input_mode = rng.choice(axes.input_modes)

    max_steps = _pick_max_steps(
        target_difficulty=target_difficulty,
        axes_range=(step_lo, step_hi),
        rng=rng,
    )

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
