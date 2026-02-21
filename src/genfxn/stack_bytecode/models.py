from enum import Enum, IntEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

_INT_RANGE_FIELDS = (
    "value_range",
    "list_length_range",
    "program_length_range",
    "const_range",
    "max_step_count_range",
)
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1


def _validate_no_bool_int_range_bounds(data: Any) -> None:
    if not isinstance(data, dict):
        return

    for field_name in _INT_RANGE_FIELDS:
        value = data.get(field_name)
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            continue
        low, high = value
        if isinstance(low, bool) or isinstance(high, bool):
            raise ValueError(
                f"{field_name}: bool is not allowed for int range bounds"
            )


class InstructionOp(str, Enum):
    PUSH_CONST = "push_const"
    LOAD_INPUT = "load_input"
    DUP = "dup"
    SWAP = "swap"
    POP = "pop"
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    MOD = "mod"
    NEG = "neg"
    ABS = "abs"
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    IS_ZERO = "is_zero"
    JUMP = "jump"
    JUMP_IF_ZERO = "jump_if_zero"
    JUMP_IF_NONZERO = "jump_if_nonzero"
    HALT = "halt"


class JumpTargetMode(str, Enum):
    ERROR = "error"
    CLAMP = "clamp"
    WRAP = "wrap"


class InputMode(str, Enum):
    DIRECT = "direct"
    CYCLIC = "cyclic"


class RuntimeStatus(IntEnum):
    OK = 0
    STEP_LIMIT = 1
    STACK_UNDERFLOW = 2
    BAD_JUMP_TARGET = 3
    DIV_OR_MOD_BY_ZERO = 4
    INVALID_INPUT_INDEX = 5
    EMPTY_STACK_ON_HALT = 6


class Instruction(BaseModel):
    op: InstructionOp
    value: int | None = Field(default=None, ge=INT64_MIN, le=INT64_MAX)
    index: int | None = Field(default=None, ge=INT64_MIN, le=INT64_MAX)
    target: int | None = Field(default=None, ge=INT64_MIN, le=INT64_MAX)

    @model_validator(mode="after")
    def validate_fields(self) -> "Instruction":
        needs_value = {InstructionOp.PUSH_CONST}
        needs_index = {InstructionOp.LOAD_INPUT}
        needs_target = {
            InstructionOp.JUMP,
            InstructionOp.JUMP_IF_ZERO,
            InstructionOp.JUMP_IF_NONZERO,
        }

        if self.op in needs_value and self.value is None:
            raise ValueError(f"op '{self.op.value}' requires field 'value'")
        if self.op in needs_index and self.index is None:
            raise ValueError(f"op '{self.op.value}' requires field 'index'")
        if self.op in needs_target and self.target is None:
            raise ValueError(f"op '{self.op.value}' requires field 'target'")
        return self


class StackBytecodeSpec(BaseModel):
    program: list[Instruction] = Field(min_length=1)
    max_step_count: int = Field(ge=1, le=INT64_MAX, default=64)
    jump_target_mode: JumpTargetMode = JumpTargetMode.ERROR
    input_mode: InputMode = InputMode.DIRECT

    @model_validator(mode="after")
    def validate_program(self) -> "StackBytecodeSpec":
        if not any(instr.op == InstructionOp.HALT for instr in self.program):
            raise ValueError(
                "program must contain at least one 'halt' instruction"
            )
        return self


class StackBytecodeAxes(BaseModel):
    value_range: tuple[int, int] = Field(default=(-50, 50))
    list_length_range: tuple[int, int] = Field(default=(0, 8))
    program_length_range: tuple[int, int] = Field(default=(2, 12))
    const_range: tuple[int, int] = Field(default=(-10, 10))
    max_step_count_range: tuple[int, int] = Field(default=(20, 160))
    jump_target_modes: list[JumpTargetMode] = Field(
        default_factory=lambda: list(JumpTargetMode)
    )
    input_modes: list[InputMode] = Field(
        default_factory=lambda: list(InputMode)
    )

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "StackBytecodeAxes":
        for name in (
            "value_range",
            "list_length_range",
            "program_length_range",
            "const_range",
            "max_step_count_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.list_length_range[0] < 0:
            raise ValueError("list_length_range: low must be >= 0")
        if self.program_length_range[0] < 1:
            raise ValueError("program_length_range: low must be >= 1")
        if self.max_step_count_range[0] < 1:
            raise ValueError("max_step_count_range: low must be >= 1")
        if self.max_step_count_range[1] > INT64_MAX:
            raise ValueError(
                f"max_step_count_range: high must be <= {INT64_MAX}"
            )

        if not self.jump_target_modes:
            raise ValueError("jump_target_modes must not be empty")
        if not self.input_modes:
            raise ValueError("input_modes must not be empty")

        return self
