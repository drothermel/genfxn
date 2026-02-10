from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from genfxn.core.int32 import (
    i32_abs,
    i32_add,
    i32_clip,
    i32_mul,
    i32_neg,
    wrap_i32,
)


class TransformIdentity(BaseModel):
    kind: Literal["identity"] = "identity"


class TransformAbs(BaseModel):
    kind: Literal["abs"] = "abs"


class TransformShift(BaseModel):
    kind: Literal["shift"] = "shift"
    offset: int


class TransformClip(BaseModel):
    kind: Literal["clip"] = "clip"
    low: int
    high: int

    @model_validator(mode="after")
    def validate_bounds(self) -> "TransformClip":
        if self.low > self.high:
            raise ValueError(f"low ({self.low}) must be <= high ({self.high})")
        return self


class TransformNegate(BaseModel):
    kind: Literal["negate"] = "negate"


class TransformScale(BaseModel):
    kind: Literal["scale"] = "scale"
    factor: int


_AtomicTransformUnion = (
    TransformIdentity
    | TransformAbs
    | TransformShift
    | TransformClip
    | TransformNegate
    | TransformScale
)
TransformAtom = Annotated[_AtomicTransformUnion, Field(discriminator="kind")]


class TransformPipeline(BaseModel):
    kind: Literal["pipeline"] = "pipeline"
    steps: list[TransformAtom]

    @model_validator(mode="after")
    def validate_step_count(self) -> "TransformPipeline":
        if not (2 <= len(self.steps) <= 3):
            raise ValueError(
                f"pipeline requires 2-3 steps, got {len(self.steps)}"
            )
        return self


class TransformType(str, Enum):
    IDENTITY = TransformIdentity.model_fields["kind"].default
    ABS = TransformAbs.model_fields["kind"].default
    SHIFT = TransformShift.model_fields["kind"].default
    CLIP = TransformClip.model_fields["kind"].default
    NEGATE = TransformNegate.model_fields["kind"].default
    SCALE = TransformScale.model_fields["kind"].default
    PIPELINE = TransformPipeline.model_fields["kind"].default


Transform = Annotated[
    TransformIdentity
    | TransformAbs
    | TransformShift
    | TransformClip
    | TransformNegate
    | TransformScale
    | TransformPipeline,
    Field(discriminator="kind"),
]


def eval_transform(t: Transform, x: int, *, int32_wrap: bool = False) -> int:
    if int32_wrap:
        x = wrap_i32(x)

    match t:
        case TransformIdentity():
            return x
        case TransformAbs():
            if int32_wrap:
                return i32_abs(x)
            return abs(x)
        case TransformShift(offset=o):
            if int32_wrap:
                return i32_add(x, o)
            return x + o
        case TransformClip(low=lo, high=hi):
            if int32_wrap:
                return i32_clip(x, lo, hi)
            clipped = max(lo, min(hi, x))
            return clipped
        case TransformNegate():
            if int32_wrap:
                return i32_neg(x)
            return -x
        case TransformScale(factor=f):
            if int32_wrap:
                return i32_mul(x, f)
            return x * f
        case TransformPipeline(steps=steps):
            result = x
            for step in steps:
                result = eval_transform(
                    step, result, int32_wrap=int32_wrap
                )
            return result
        case _:
            raise ValueError(f"Unknown transform: {t}")


def render_transform(t: Transform, var: str = "x") -> str:
    match t:
        case TransformIdentity():
            return var
        case TransformAbs():
            return f"abs({var})"
        case TransformShift(offset=o):
            if o >= 0:
                return f"{var} + {o}"
            return f"{var} - {-o}"
        case TransformClip(low=lo, high=hi):
            return f"max({lo}, min({hi}, {var}))"
        case TransformNegate():
            return f"-{var}"
        case TransformScale(factor=f):
            return f"{var} * {f}"
        case TransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_transform(step, expr)
            return expr
        case _:
            raise ValueError(f"Unknown transform: {t}")
