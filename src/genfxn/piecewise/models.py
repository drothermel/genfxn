from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from genfxn.core.int64_safety import (
    abs_range,
    add_ranges,
    fits_signed_i64,
    mul_ranges,
    square_range,
)
from genfxn.core.predicates import Predicate

INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1
INT32_MAX = (1 << 31) - 1


class ExprType(str, Enum):
    AFFINE = "affine"
    QUADRATIC = "quadratic"
    ABS = "abs"
    MOD = "mod"


_INT_RANGE_FIELDS = (
    "value_range",
    "coeff_range",
    "threshold_range",
    "divisor_range",
)


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


# --- Expression Types ---


class ExprAffine(BaseModel):
    kind: Literal["affine"] = "affine"
    a: int = Field(
        description="Coefficient for x",
        ge=INT64_MIN,
        le=INT64_MAX,
    )
    b: int = Field(
        description="Constant term",
        ge=INT64_MIN,
        le=INT64_MAX,
    )


class ExprQuadratic(BaseModel):
    kind: Literal["quadratic"] = "quadratic"
    a: int = Field(
        description="Coefficient for x^2",
        ge=INT64_MIN,
        le=INT64_MAX,
    )
    b: int = Field(
        description="Coefficient for x",
        ge=INT64_MIN,
        le=INT64_MAX,
    )
    c: int = Field(
        description="Constant term",
        ge=INT64_MIN,
        le=INT64_MAX,
    )


class ExprAbs(BaseModel):
    kind: Literal["abs"] = "abs"
    a: int = Field(
        description="Coefficient for abs(x)",
        ge=INT64_MIN,
        le=INT64_MAX,
    )
    b: int = Field(
        description="Constant term",
        ge=INT64_MIN,
        le=INT64_MAX,
    )


class ExprMod(BaseModel):
    kind: Literal["mod"] = "mod"
    divisor: int = Field(
        description="Divisor for x % divisor",
        ge=1,
        le=INT32_MAX,
    )
    a: int = Field(
        description="Coefficient for (x % divisor)",
        ge=INT64_MIN,
        le=INT64_MAX,
    )
    b: int = Field(
        description="Constant term",
        ge=INT64_MIN,
        le=INT64_MAX,
    )


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
    expr_types: list[ExprType] = Field(
        default_factory=lambda: [ExprType.AFFINE]
    )
    value_range: tuple[int, int] = Field(default=(-100, 100))
    coeff_range: tuple[int, int] = Field(default=(-5, 5))
    threshold_range: tuple[int, int] = Field(default=(-50, 50))
    divisor_range: tuple[int, int] = Field(default=(2, 10))

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "PiecewiseAxes":
        if not self.expr_types:
            raise ValueError("expr_types must not be empty")

        for name in (
            "value_range",
            "coeff_range",
            "threshold_range",
            "divisor_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")
            if lo < INT64_MIN:
                raise ValueError(f"{name}: low ({lo}) must be >= {INT64_MIN}")
            if hi > INT64_MAX:
                raise ValueError(f"{name}: high ({hi}) must be <= {INT64_MAX}")

        div_lo, div_hi = self.divisor_range
        if div_lo < 1:
            raise ValueError(f"divisor_range: low ({div_lo}) must be >= 1")
        if div_hi > INT32_MAX:
            raise ValueError(
                f"divisor_range: high ({div_hi}) must be <= {INT32_MAX}"
            )

        lo, hi = self.threshold_range
        available = hi - lo + 1
        if self.n_branches > available:
            raise ValueError(
                f"n_branches ({self.n_branches}) exceeds available thresholds "
                f"in threshold_range ({available})"
            )

        if self.coeff_range[0] == INT64_MIN:
            raise ValueError(
                "coeff_range: low must be > INT64_MIN to keep Java/Rust "
                "literal rendering overflow-safe"
            )

        value_range = self.value_range
        coeff_range = self.coeff_range

        def _raise_overflow(expr_type: ExprType) -> None:
            raise ValueError(
                "Numeric contract violation: expr_types includes "
                f"'{expr_type.value}' but value_range={value_range} and "
                f"coeff_range={coeff_range} can overflow signed 64-bit "
                "arithmetic. Tighten ranges."
            )

        def _ensure_i64(
            expr_type: ExprType, output_range: tuple[int, int]
        ) -> None:
            if not fits_signed_i64(output_range):
                _raise_overflow(expr_type)

        for expr_type in self.expr_types:
            if expr_type == ExprType.AFFINE:
                output_range = add_ranges(
                    mul_ranges(coeff_range, value_range),
                    coeff_range,
                )
                _ensure_i64(expr_type, output_range)
                continue

            if expr_type == ExprType.QUADRATIC:
                x_sq = square_range(value_range)
                ax2 = mul_ranges(coeff_range, x_sq)
                bx = mul_ranges(coeff_range, value_range)
                output_range = add_ranges(add_ranges(ax2, bx), coeff_range)
                _ensure_i64(expr_type, output_range)
                continue

            if expr_type == ExprType.ABS:
                if value_range[0] == INT64_MIN:
                    raise ValueError(
                        "value_range: low must be > INT64_MIN when "
                        "expr_types includes 'abs'"
                    )
                output_range = add_ranges(
                    mul_ranges(coeff_range, abs_range(value_range)),
                    coeff_range,
                )
                _ensure_i64(expr_type, output_range)
                continue

            if expr_type == ExprType.MOD:
                mod_term = (0, self.divisor_range[1] - 1)
                output_range = add_ranges(
                    mul_ranges(coeff_range, mod_term),
                    coeff_range,
                )
                _ensure_i64(expr_type, output_range)
        return self
