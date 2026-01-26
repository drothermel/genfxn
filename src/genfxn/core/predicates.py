from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class PredicateEven(BaseModel):
    kind: Literal["even"] = "even"


class PredicateOdd(BaseModel):
    kind: Literal["odd"] = "odd"


class PredicateLt(BaseModel):
    kind: Literal["lt"] = "lt"
    value: int


class PredicateLe(BaseModel):
    kind: Literal["le"] = "le"
    value: int


class PredicateGt(BaseModel):
    kind: Literal["gt"] = "gt"
    value: int


class PredicateGe(BaseModel):
    kind: Literal["ge"] = "ge"
    value: int


class PredicateModEq(BaseModel):
    kind: Literal["mod_eq"] = "mod_eq"
    divisor: int
    remainder: int

    @field_validator("divisor")
    @classmethod
    def divisor_nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("divisor must be non-zero")
        return v


class PredicateInSet(BaseModel):
    model_config = {"frozen": True}
    kind: Literal["in_set"] = "in_set"
    values: frozenset[int]


class PredicateType(str, Enum):
    EVEN = PredicateEven.model_fields["kind"].default
    ODD = PredicateOdd.model_fields["kind"].default
    LT = PredicateLt.model_fields["kind"].default
    LE = PredicateLe.model_fields["kind"].default
    GT = PredicateGt.model_fields["kind"].default
    GE = PredicateGe.model_fields["kind"].default
    MOD_EQ = PredicateModEq.model_fields["kind"].default
    IN_SET = PredicateInSet.model_fields["kind"].default


Predicate = Annotated[
    PredicateEven
    | PredicateOdd
    | PredicateLt
    | PredicateLe
    | PredicateGt
    | PredicateGe
    | PredicateModEq
    | PredicateInSet,
    Field(discriminator="kind"),
]


def eval_predicate(pred: Predicate, x: int) -> bool:
    match pred:
        case PredicateEven():
            return x % 2 == 0
        case PredicateOdd():
            return x % 2 == 1
        case PredicateLt(value=v):
            return x < v
        case PredicateLe(value=v):
            return x <= v
        case PredicateGt(value=v):
            return x > v
        case PredicateGe(value=v):
            return x >= v
        case PredicateModEq(divisor=d, remainder=r):
            return x % d == r
        case PredicateInSet(values=vals):
            return x in vals
        case _:
            raise ValueError(f"Unknown predicate: {pred}")


def render_predicate(pred: Predicate, var: str = "x") -> str:
    match pred:
        case PredicateEven():
            return f"{var} % 2 == 0"
        case PredicateOdd():
            return f"{var} % 2 == 1"
        case PredicateLt(value=v):
            return f"{var} < {v}"
        case PredicateLe(value=v):
            return f"{var} <= {v}"
        case PredicateGt(value=v):
            return f"{var} > {v}"
        case PredicateGe(value=v):
            return f"{var} >= {v}"
        case PredicateModEq(divisor=d, remainder=r):
            return f"{var} % {d} == {r}"
        case PredicateInSet(values=vals):
            return f"{var} in {{{', '.join(map(str, sorted(vals)))}}}"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")
