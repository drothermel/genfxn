"""String predicates for the stringrules family.

These predicates check conditions on strings using common string methods.
No regex is used to keep the DSL simple and query generation tractable.
"""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class StringPredicateStartsWith(BaseModel):
    kind: Literal["starts_with"] = "starts_with"
    prefix: str


class StringPredicateEndsWith(BaseModel):
    kind: Literal["ends_with"] = "ends_with"
    suffix: str


class StringPredicateContains(BaseModel):
    kind: Literal["contains"] = "contains"
    substring: str


class StringPredicateIsAlpha(BaseModel):
    kind: Literal["is_alpha"] = "is_alpha"


class StringPredicateIsDigit(BaseModel):
    kind: Literal["is_digit"] = "is_digit"


class StringPredicateIsUpper(BaseModel):
    kind: Literal["is_upper"] = "is_upper"


class StringPredicateIsLower(BaseModel):
    kind: Literal["is_lower"] = "is_lower"


class StringPredicateLengthCmp(BaseModel):
    kind: Literal["length_cmp"] = "length_cmp"
    op: Literal["lt", "le", "gt", "ge", "eq"]
    value: int

    @model_validator(mode="after")
    def validate_value(self) -> "StringPredicateLengthCmp":
        if self.value < 0:
            raise ValueError(f"value must be >= 0, got {self.value}")
        return self


class StringPredicateType(str, Enum):
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    CONTAINS = "contains"
    IS_ALPHA = "is_alpha"
    IS_DIGIT = "is_digit"
    IS_UPPER = "is_upper"
    IS_LOWER = "is_lower"
    LENGTH_CMP = "length_cmp"


StringPredicate = Annotated[
    StringPredicateStartsWith
    | StringPredicateEndsWith
    | StringPredicateContains
    | StringPredicateIsAlpha
    | StringPredicateIsDigit
    | StringPredicateIsUpper
    | StringPredicateIsLower
    | StringPredicateLengthCmp,
    Field(discriminator="kind"),
]


def eval_string_predicate(pred: StringPredicate, s: str) -> bool:
    match pred:
        case StringPredicateStartsWith(prefix=p):
            return s.startswith(p)
        case StringPredicateEndsWith(suffix=suf):
            return s.endswith(suf)
        case StringPredicateContains(substring=sub):
            return sub in s
        case StringPredicateIsAlpha():
            return len(s) > 0 and s.isalpha()
        case StringPredicateIsDigit():
            return len(s) > 0 and s.isdigit()
        case StringPredicateIsUpper():
            return len(s) > 0 and s.isupper()
        case StringPredicateIsLower():
            return len(s) > 0 and s.islower()
        case StringPredicateLengthCmp(op=op, value=v):
            length = len(s)
            match op:
                case "lt":
                    return length < v
                case "le":
                    return length <= v
                case "gt":
                    return length > v
                case "ge":
                    return length >= v
                case "eq":
                    return length == v
                case _:
                    return False
        case _:
            raise ValueError(f"Unknown string predicate: {pred}")


def render_string_predicate(pred: StringPredicate, var: str = "s") -> str:
    match pred:
        case StringPredicateStartsWith(prefix=p):
            return f"{var}.startswith({p!r})"
        case StringPredicateEndsWith(suffix=suf):
            return f"{var}.endswith({suf!r})"
        case StringPredicateContains(substring=sub):
            return f"{sub!r} in {var}"
        case StringPredicateIsAlpha():
            return f"{var}.isalpha()"
        case StringPredicateIsDigit():
            return f"{var}.isdigit()"
        case StringPredicateIsUpper():
            return f"{var}.isupper()"
        case StringPredicateIsLower():
            return f"{var}.islower()"
        case StringPredicateLengthCmp(op=op, value=v):
            op_map = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "=="}
            return f"len({var}) {op_map[op]} {v}"
        case _:
            raise ValueError(f"Unknown string predicate: {pred}")
