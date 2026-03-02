from genfxn.stack_bytecode.models import (
    InputMode,
    Instruction,
    InstructionOp,
    JumpTargetMode,
    RuntimeStatus,
    StackBytecodeSpec,
)

RuntimeResult = tuple[int, int]
_I64_MASK = (1 << 64) - 1
_I64_MIN = -(1 << 63)


def _wrap_i64(value: int) -> int:
    wrapped = value & _I64_MASK
    if wrapped >= (1 << 63):
        return wrapped - (1 << 64)
    return wrapped


def _div_trunc_zero_i64(a: int, b: int) -> int:
    sign = -1 if (a < 0) ^ (b < 0) else 1
    if a == _I64_MIN and b == -1:
        return _I64_MIN
    return _wrap_i64(sign * (abs(a) // abs(b)))


def _mod_trunc_zero_i64(a: int, b: int) -> int:
    if a == _I64_MIN and b == -1:
        return 0
    return _wrap_i64(a - _div_trunc_zero_i64(a, b) * b)


def _normalize_jump_target(
    target: int,
    program_len: int,
    mode: JumpTargetMode,
) -> int | None:
    if mode == JumpTargetMode.ERROR:
        if 0 <= target < program_len:
            return target
        return None
    if mode == JumpTargetMode.CLAMP:
        if target < 0:
            return 0
        if target >= program_len:
            return program_len - 1
        return target
    return target % program_len


def _load_input(index: int, xs: list[int], mode: InputMode) -> int | None:
    if mode == InputMode.DIRECT:
        if 0 <= index < len(xs):
            return xs[index]
        return None

    # CYCLIC mode
    if len(xs) == 0:
        return None
    return xs[index % len(xs)]


def _pop1(stack: list[int]) -> tuple[bool, int]:
    if not stack:
        return False, 0
    return True, stack.pop()


def _pop2(stack: list[int]) -> tuple[bool, int, int]:
    if len(stack) < 2:
        return False, 0, 0
    b = stack.pop()
    a = stack.pop()
    return True, a, b


def eval_stack_bytecode(
    spec: StackBytecodeSpec, xs: list[int]
) -> RuntimeResult:
    program = spec.program
    stack: list[int] = []
    pc = 0
    steps = 0
    program_len = len(program)

    while steps < spec.max_step_count:
        if not (0 <= pc < program_len):
            return RuntimeStatus.BAD_JUMP_TARGET, 0

        instr = program[pc]
        op = instr.op
        steps += 1

        if op == InstructionOp.PUSH_CONST:
            value = instr.value if instr.value is not None else 0
            stack.append(_wrap_i64(value))
            pc += 1
            continue

        if op == InstructionOp.LOAD_INPUT:
            idx = instr.index if instr.index is not None else 0
            value = _load_input(idx, xs, spec.input_mode)
            if value is None:
                return RuntimeStatus.INVALID_INPUT_INDEX, 0
            stack.append(_wrap_i64(value))
            pc += 1
            continue

        if op == InstructionOp.DUP:
            ok, a = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(a)
            stack.append(a)
            pc += 1
            continue

        if op == InstructionOp.SWAP:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(b)
            stack.append(a)
            pc += 1
            continue

        if op == InstructionOp.POP:
            ok, _ = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            pc += 1
            continue

        if op == InstructionOp.ADD:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(_wrap_i64(a + b))
            pc += 1
            continue

        if op == InstructionOp.SUB:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(_wrap_i64(a - b))
            pc += 1
            continue

        if op == InstructionOp.MUL:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(_wrap_i64(a * b))
            pc += 1
            continue

        if op == InstructionOp.DIV:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            if b == 0:
                return RuntimeStatus.DIV_OR_MOD_BY_ZERO, 0
            stack.append(_div_trunc_zero_i64(a, b))
            pc += 1
            continue

        if op == InstructionOp.MOD:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            if b == 0:
                return RuntimeStatus.DIV_OR_MOD_BY_ZERO, 0
            stack.append(_mod_trunc_zero_i64(a, b))
            pc += 1
            continue

        if op == InstructionOp.NEG:
            ok, a = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(_wrap_i64(-a))
            pc += 1
            continue

        if op == InstructionOp.ABS:
            ok, a = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(_wrap_i64(abs(a)))
            pc += 1
            continue

        if op == InstructionOp.EQ:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(1 if a == b else 0)
            pc += 1
            continue

        if op == InstructionOp.GT:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(1 if a > b else 0)
            pc += 1
            continue

        if op == InstructionOp.LT:
            ok, a, b = _pop2(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(1 if a < b else 0)
            pc += 1
            continue

        if op == InstructionOp.IS_ZERO:
            ok, a = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            stack.append(1 if a == 0 else 0)
            pc += 1
            continue

        if op == InstructionOp.JUMP:
            target = instr.target if instr.target is not None else 0
            resolved = _normalize_jump_target(
                target, program_len, spec.jump_target_mode
            )
            if resolved is None:
                return RuntimeStatus.BAD_JUMP_TARGET, 0
            pc = resolved
            continue

        if op == InstructionOp.JUMP_IF_ZERO:
            ok, a = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            if a == 0:
                target = instr.target if instr.target is not None else 0
                resolved = _normalize_jump_target(
                    target, program_len, spec.jump_target_mode
                )
                if resolved is None:
                    return RuntimeStatus.BAD_JUMP_TARGET, 0
                pc = resolved
            else:
                pc += 1
            continue

        if op == InstructionOp.JUMP_IF_NONZERO:
            ok, a = _pop1(stack)
            if not ok:
                return RuntimeStatus.STACK_UNDERFLOW, 0
            if a != 0:
                target = instr.target if instr.target is not None else 0
                resolved = _normalize_jump_target(
                    target, program_len, spec.jump_target_mode
                )
                if resolved is None:
                    return RuntimeStatus.BAD_JUMP_TARGET, 0
                pc = resolved
            else:
                pc += 1
            continue

        if op == InstructionOp.HALT:
            if not stack:
                return RuntimeStatus.EMPTY_STACK_ON_HALT, 0
            return RuntimeStatus.OK, stack[-1]

        # Unknown op should not happen with model validation.
        return RuntimeStatus.BAD_JUMP_TARGET, 0

    return RuntimeStatus.STEP_LIMIT, 0


def eval_instruction(instr: Instruction, stack: list[int]) -> list[int]:
    """Execute one supported single-step op on a copy of ``stack``.

    This helper currently supports only ``InstructionOp.PUSH_CONST`` (push
    ``instr.value`` or 0) and ``InstructionOp.POP`` (raises ``ValueError``
    on underflow). Control-flow and all other ops are unsupported.
    """
    out = list(stack)
    op = instr.op
    if op == InstructionOp.PUSH_CONST:
        out.append(_wrap_i64(instr.value if instr.value is not None else 0))
        return out
    if op == InstructionOp.POP:
        if not out:
            raise ValueError("stack underflow")
        out.pop()
        return out
    raise ValueError(f"Unsupported single-step instruction: {op.value}")
