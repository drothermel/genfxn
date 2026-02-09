from enum import Enum

from pydantic import BaseModel, Field, model_validator


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
    arg: int | None = None

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
    target_difficulty: int | None = Field(default=None, ge=1, le=5)
    width_choices: list[int] = Field(default_factory=lambda: [8, 16, 32])
    n_ops_range: tuple[int, int] = Field(default=(2, 6))
    value_range: tuple[int, int] = Field(default=(-1024, 1024))
    mask_range: tuple[int, int] = Field(default=(0, 65_535))
    shift_range: tuple[int, int] = Field(default=(0, 63))
    allowed_ops: list[BitOp] = Field(default_factory=lambda: list(BitOp))

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

        return self
