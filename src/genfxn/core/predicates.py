from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


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


class PredicateInSet(BaseModel):
    model_config = {"frozen": True}
    kind: Literal["in_set"] = "in_set"
    values: frozenset[int]


Predicate = Annotated[
    Union[
        PredicateEven,
        PredicateOdd,
        PredicateLt,
        PredicateLe,
        PredicateGt,
        PredicateGe,
        PredicateModEq,
        PredicateInSet,
    ],
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
            return f"{var} in {set(sorted(vals))}"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")
