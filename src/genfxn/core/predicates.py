from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


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


_AtomicPredUnion = (
    PredicateEven
    | PredicateOdd
    | PredicateLt
    | PredicateLe
    | PredicateGt
    | PredicateGe
    | PredicateModEq
    | PredicateInSet
)
PredicateAtom = Annotated[_AtomicPredUnion, Field(discriminator="kind")]


class PredicateNot(BaseModel):
    kind: Literal["not"] = "not"
    operand: PredicateAtom


class PredicateAnd(BaseModel):
    kind: Literal["and"] = "and"
    operands: list[PredicateAtom]

    @model_validator(mode="after")
    def validate_operand_count(self) -> "PredicateAnd":
        if not (2 <= len(self.operands) <= 3):
            raise ValueError(
                f"and requires 2-3 operands, got {len(self.operands)}"
            )
        return self


class PredicateOr(BaseModel):
    kind: Literal["or"] = "or"
    operands: list[PredicateAtom]

    @model_validator(mode="after")
    def validate_operand_count(self) -> "PredicateOr":
        if not (2 <= len(self.operands) <= 3):
            raise ValueError(
                f"or requires 2-3 operands, got {len(self.operands)}"
            )
        return self


class PredicateType(str, Enum):
    EVEN = "even"
    ODD = "odd"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    MOD_EQ = "mod_eq"
    IN_SET = "in_set"
    NOT = "not"
    AND = "and"
    OR = "or"


Predicate = Annotated[
    PredicateEven
    | PredicateOdd
    | PredicateLt
    | PredicateLe
    | PredicateGt
    | PredicateGe
    | PredicateModEq
    | PredicateInSet
    | PredicateNot
    | PredicateAnd
    | PredicateOr,
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
        case PredicateNot(operand=op):
            return not eval_predicate(op, x)
        case PredicateAnd(operands=ops):
            return all(eval_predicate(op, x) for op in ops)
        case PredicateOr(operands=ops):
            return any(eval_predicate(op, x) for op in ops)
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
        case PredicateNot(operand=op):
            return f"not ({render_predicate(op, var)})"
        case PredicateAnd(operands=ops):
            return f"({' and '.join(render_predicate(op, var) for op in ops)})"
        case PredicateOr(operands=ops):
            return f"({' or '.join(render_predicate(op, var) for op in ops)})"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")


class ThresholdInfo(BaseModel):
    """Threshold information extracted from a comparison predicate."""

    kind: Literal["lt", "le", "gt", "ge"] = Field(
        description="Comparison operator kind"
    )
    value: int = Field(description="Threshold value")


def get_threshold(pred: Predicate) -> ThresholdInfo | None:
    """Extract threshold info from comparison predicates.

    Returns ThresholdInfo for lt/le/gt/ge predicates, None for others.
    """
    match pred:
        case PredicateLt(value=v):
            return ThresholdInfo(kind="lt", value=v)
        case PredicateLe(value=v):
            return ThresholdInfo(kind="le", value=v)
        case PredicateGt(value=v):
            return ThresholdInfo(kind="gt", value=v)
        case PredicateGe(value=v):
            return ThresholdInfo(kind="ge", value=v)
        case _:
            return None
