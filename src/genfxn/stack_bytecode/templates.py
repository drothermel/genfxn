import random

from genfxn.stack_bytecode.models import Instruction, InstructionOp


def stack_template_program(
    difficulty: int,
    rng: random.Random,
) -> list[Instruction]:
    if difficulty <= 1:
        c = rng.randint(-10, 10)
        return [
            Instruction(op=InstructionOp.PUSH_CONST, value=c),
            Instruction(op=InstructionOp.HALT),
        ]
    if difficulty == 2:
        c = rng.randint(-5, 5)
        return [
            Instruction(op=InstructionOp.LOAD_INPUT, index=0),
            Instruction(op=InstructionOp.PUSH_CONST, value=c),
            Instruction(op=InstructionOp.ADD),
            Instruction(op=InstructionOp.HALT),
        ]
    if difficulty == 3:
        c = rng.randint(1, 5)
        return [
            Instruction(op=InstructionOp.LOAD_INPUT, index=0),
            Instruction(op=InstructionOp.DUP),
            Instruction(op=InstructionOp.PUSH_CONST, value=c),
            Instruction(op=InstructionOp.MUL),
            Instruction(op=InstructionOp.SUB),
            Instruction(op=InstructionOp.HALT),
        ]
    if difficulty == 4:
        c = rng.randint(1, 5)
        return [
            Instruction(op=InstructionOp.LOAD_INPUT, index=0),
            Instruction(op=InstructionOp.JUMP_IF_ZERO, target=6),
            Instruction(op=InstructionOp.LOAD_INPUT, index=1),
            Instruction(op=InstructionOp.PUSH_CONST, value=c),
            Instruction(op=InstructionOp.ADD),
            Instruction(op=InstructionOp.HALT),
            Instruction(op=InstructionOp.PUSH_CONST, value=0),
            Instruction(op=InstructionOp.HALT),
        ]
    c = rng.randint(1, 3)
    return [
        Instruction(op=InstructionOp.PUSH_CONST, value=0),
        Instruction(op=InstructionOp.LOAD_INPUT, index=0),
        Instruction(op=InstructionOp.JUMP_IF_ZERO, target=10),
        Instruction(op=InstructionOp.LOAD_INPUT, index=0),
        Instruction(op=InstructionOp.PUSH_CONST, value=c),
        Instruction(op=InstructionOp.SUB),
        Instruction(op=InstructionOp.JUMP_IF_NONZERO, target=3),
        Instruction(op=InstructionOp.PUSH_CONST, value=1),
        Instruction(op=InstructionOp.JUMP, target=10),
        Instruction(op=InstructionOp.PUSH_CONST, value=-1),
        Instruction(op=InstructionOp.HALT),
    ]
