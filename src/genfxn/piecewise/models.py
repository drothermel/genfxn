from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from genfxn.core.predicates import Predicate


class ExprType(str, Enum):
    AFFINE = "affine"
    QUADRATIC = "quadratic"
    ABS = "abs"
    MOD = "mod"


# --- Expression Types ---


class ExprAffine(BaseModel):
    kind: Literal["affine"] = "affine"
    a: int = Field(description="Coefficient for x")
    b: int = Field(description="Constant term")


class ExprQuadratic(BaseModel):
    kind: Literal["quadratic"] = "quadratic"
    a: int = Field(description="Coefficient for x^2")
    b: int = Field(description="Coefficient for x")
    c: int = Field(description="Constant term")


class ExprAbs(BaseModel):
    kind: Literal["abs"] = "abs"
    a: int = Field(description="Coefficient for abs(x)")
    b: int = Field(description="Constant term")


class ExprMod(BaseModel):
    kind: Literal["mod"] = "mod"
    divisor: int = Field(description="Divisor for x % divisor", gt=0)
    a: int = Field(description="Coefficient for (x % divisor)")
    b: int = Field(description="Constant term")


Expression = Annotated[
    ExprAffine | ExprQuadratic | ExprAbs | ExprMod,
    Field(discriminator="kind"),
]


# --- Branch and Spec ---


class Branch(BaseModel):
    condition: Predicate
    expr: Expression


class PiecewiseSpec(BaseModel):
    branches: list[Branch]
    default_expr: Expression


# --- Axes (sampling configuration) ---


class PiecewiseAxes(BaseModel):
    n_branches: int = Field(default=2, ge=1, le=5)
    expr_types: list[ExprType] = Field(default_factory=lambda: [ExprType.AFFINE])
    value_range: tuple[int, int] = Field(default=(-100, 100))
    coeff_range: tuple[int, int] = Field(default=(-5, 5))
    threshold_range: tuple[int, int] = Field(default=(-50, 50))
    divisor_range: tuple[int, int] = Field(default=(2, 10))
