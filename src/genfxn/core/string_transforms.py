from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class StringTransformIdentity(BaseModel):
    kind: Literal["identity"] = "identity"


class StringTransformLowercase(BaseModel):
    kind: Literal["lowercase"] = "lowercase"


class StringTransformUppercase(BaseModel):
    kind: Literal["uppercase"] = "uppercase"


class StringTransformCapitalize(BaseModel):
    kind: Literal["capitalize"] = "capitalize"


class StringTransformSwapcase(BaseModel):
    kind: Literal["swapcase"] = "swapcase"


class StringTransformReverse(BaseModel):
    kind: Literal["reverse"] = "reverse"


class StringTransformReplace(BaseModel):
    kind: Literal["replace"] = "replace"
    old: str
    new: str


class StringTransformStrip(BaseModel):
    kind: Literal["strip"] = "strip"
    chars: str | None = None


class StringTransformPrepend(BaseModel):
    kind: Literal["prepend"] = "prepend"
    prefix: str


class StringTransformAppend(BaseModel):
    kind: Literal["append"] = "append"
    suffix: str


class StringTransformType(str, Enum):
    IDENTITY = "identity"
    LOWERCASE = "lowercase"
    UPPERCASE = "uppercase"
    CAPITALIZE = "capitalize"
    SWAPCASE = "swapcase"
    REVERSE = "reverse"
    REPLACE = "replace"
    STRIP = "strip"
    PREPEND = "prepend"
    APPEND = "append"


StringTransform = Annotated[
    StringTransformIdentity
    | StringTransformLowercase
    | StringTransformUppercase
    | StringTransformCapitalize
    | StringTransformSwapcase
    | StringTransformReverse
    | StringTransformReplace
    | StringTransformStrip
    | StringTransformPrepend
    | StringTransformAppend,
    Field(discriminator="kind"),
]


def eval_string_transform(t: StringTransform, s: str) -> str:
    match t:
        case StringTransformIdentity():
            return s
        case StringTransformLowercase():
            return s.lower()
        case StringTransformUppercase():
            return s.upper()
        case StringTransformCapitalize():
            return s.capitalize()
        case StringTransformSwapcase():
            return s.swapcase()
        case StringTransformReverse():
            return s[::-1]
        case StringTransformReplace(old=old, new=new):
            return s.replace(old, new)
        case StringTransformStrip(chars=chars):
            return s.strip(chars)
        case StringTransformPrepend(prefix=prefix):
            return prefix + s
        case StringTransformAppend(suffix=suffix):
            return s + suffix
        case _:
            raise ValueError(f"Unknown string transform: {t}")


def render_string_transform(t: StringTransform, var: str = "s") -> str:
    match t:
        case StringTransformIdentity():
            return var
        case StringTransformLowercase():
            return f"{var}.lower()"
        case StringTransformUppercase():
            return f"{var}.upper()"
        case StringTransformCapitalize():
            return f"{var}.capitalize()"
        case StringTransformSwapcase():
            return f"{var}.swapcase()"
        case StringTransformReverse():
            return f"{var}[::-1]"
        case StringTransformReplace(old=old, new=new):
            return f"{var}.replace({old!r}, {new!r})"
        case StringTransformStrip(chars=chars):
            if chars is None:
                return f"{var}.strip()"
            return f"{var}.strip({chars!r})"
        case StringTransformPrepend(prefix=prefix):
            return f"{prefix!r} + {var}"
        case StringTransformAppend(suffix=suffix):
            return f"{var} + {suffix!r}"
        case _:
            raise ValueError(f"Unknown string transform: {t}")
