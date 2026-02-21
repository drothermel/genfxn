from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

_INT_RANGE_FIELDS = (
    "n_ops_range",
    "value_range",
    "mask_range",
    "shift_range",
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


class BitOp(str, Enum):
    AND_MASK = "and_mask"
    OR_MASK = "or_mask"
    XOR_MASK = "xor_mask"
    SHL = "shl"
    SHR_LOGICAL = "shr_logical"
    ROTL = "rotl"
    ROTR = "rotr"
    NOT = "not"
    POPCOUNT = "popcount"
    PARITY = "parity"


class BitInstruction(BaseModel):
    op: BitOp
    arg: int | None = Field(default=None, ge=INT64_MIN, le=INT64_MAX)

    @model_validator(mode="after")
    def validate_fields(self) -> "BitInstruction":
        needs_arg = {
            BitOp.AND_MASK,
            BitOp.OR_MASK,
            BitOp.XOR_MASK,
            BitOp.SHL,
            BitOp.SHR_LOGICAL,
            BitOp.ROTL,
            BitOp.ROTR,
        }
        if self.op in needs_arg and self.arg is None:
            raise ValueError(f"op '{self.op.value}' requires field 'arg'")
        return self


class BitopsSpec(BaseModel):
    width_bits: int = Field(default=8, ge=1, le=63)
    operations: list[BitInstruction] = Field(min_length=1)


class BitopsAxes(BaseModel):
    width_choices: list[int] = Field(default_factory=lambda: [8, 16, 32])
    n_ops_range: tuple[int, int] = Field(default=(2, 6))
    value_range: tuple[int, int] = Field(default=(-1024, 1024))
    mask_range: tuple[int, int] = Field(default=(0, 65_535))
    shift_range: tuple[int, int] = Field(default=(0, 63))
    allowed_ops: list[BitOp] = Field(default_factory=lambda: list(BitOp))

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "BitopsAxes":
        if not self.width_choices:
            raise ValueError("width_choices must not be empty")
        if not self.allowed_ops:
            raise ValueError("allowed_ops must not be empty")

        for width in self.width_choices:
            if width < 1 or width > 63:
                raise ValueError("width_choices values must be in [1, 63]")

        for name in (
            "n_ops_range",
            "value_range",
            "mask_range",
            "shift_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.n_ops_range[0] < 1:
            raise ValueError("n_ops_range: low must be >= 1")

        for name in ("value_range", "mask_range", "shift_range"):
            lo, hi = getattr(self, name)
            if lo < INT64_MIN:
                raise ValueError(f"{name}: low must be >= {INT64_MIN}")
            if hi > INT64_MAX:
                raise ValueError(f"{name}: high must be <= {INT64_MAX}")

        return self
