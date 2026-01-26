from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


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


class TransformNegate(BaseModel):
    kind: Literal["negate"] = "negate"


class TransformScale(BaseModel):
    kind: Literal["scale"] = "scale"
    factor: int


Transform = Annotated[
    Union[
        TransformIdentity,
        TransformAbs,
        TransformShift,
        TransformClip,
        TransformNegate,
        TransformScale,
    ],
    Field(discriminator="kind"),
]


def eval_transform(t: Transform, x: int) -> int:
    match t:
        case TransformIdentity():
            return x
        case TransformAbs():
            return abs(x)
        case TransformShift(offset=o):
            return x + o
        case TransformClip(low=lo, high=hi):
            return max(lo, min(hi, x))
        case TransformNegate():
            return -x
        case TransformScale(factor=f):
            return x * f
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
        case _:
            raise ValueError(f"Unknown transform: {t}")
