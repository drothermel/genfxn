from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from genfxn.core.predicates import Predicate, PredicateType
from genfxn.core.transforms import Transform, TransformType

_INT_RANGE_FIELDS = (
    "value_range",
    "list_length_range",
    "threshold_range",
    "divisor_range",
    "shift_range",
    "scale_range",
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


class TemplateType(str, Enum):
    CONDITIONAL_LINEAR_SUM = "conditional_linear_sum"
    RESETTING_BEST_PREFIX_SUM = "resetting_best_prefix_sum"
    LONGEST_RUN = "longest_run"
    TOGGLE_SUM = "toggle_sum"


# --- Template Specs ---


class ConditionalLinearSumSpec(BaseModel):
    template: Literal["conditional_linear_sum"] = "conditional_linear_sum"
    predicate: Predicate
    true_transform: Transform
    false_transform: Transform
    init_value: int = 0


class ResettingBestPrefixSumSpec(BaseModel):
    template: Literal["resetting_best_prefix_sum"] = "resetting_best_prefix_sum"
    reset_predicate: Predicate
    init_value: int = 0
    value_transform: Transform | None = None


class LongestRunSpec(BaseModel):
    template: Literal["longest_run"] = "longest_run"
    match_predicate: Predicate


class ToggleSumSpec(BaseModel):
    template: Literal["toggle_sum"] = "toggle_sum"
    toggle_predicate: Predicate
    on_transform: Transform
    off_transform: Transform
    init_value: int = 0


StatefulSpec = Annotated[
    ConditionalLinearSumSpec
    | ResettingBestPrefixSumSpec
    | LongestRunSpec
    | ToggleSumSpec,
    Field(discriminator="template"),
]


# --- Axes (sampling configuration) ---


class StatefulAxes(BaseModel):
    templates: list[TemplateType] = Field(
        default_factory=lambda: list(TemplateType)
    )
    predicate_types: list[PredicateType] = Field(
        default_factory=lambda: [
            PredicateType.EVEN,
            PredicateType.ODD,
            PredicateType.LT,
            PredicateType.LE,
            PredicateType.GT,
            PredicateType.GE,
            PredicateType.MOD_EQ,
            # IN_SET excluded - not useful for element-wise predicates
        ]
    )
    transform_types: list[TransformType] = Field(
        default_factory=lambda: [
            TransformType.IDENTITY,
            TransformType.ABS,
            TransformType.SHIFT,
            TransformType.NEGATE,
            TransformType.SCALE,
            # CLIP excluded - not useful for accumulator transforms
        ]
    )
    value_range: tuple[int, int] = Field(default=(-100, 100))
    list_length_range: tuple[int, int] = Field(default=(5, 20))
    threshold_range: tuple[int, int] = Field(default=(-50, 50))
    divisor_range: tuple[int, int] = Field(default=(2, 10))
    shift_range: tuple[int, int] = Field(default=(-10, 10))
    scale_range: tuple[int, int] = Field(default=(-5, 5))
    min_composed_operands: int = Field(
        default=2, ge=2, le=5, description="Min operands for AND/OR predicates"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "StatefulAxes":
        if not self.templates:
            raise ValueError("templates must not be empty")
        if not self.predicate_types:
            raise ValueError("predicate_types must not be empty")
        if not self.transform_types:
            raise ValueError("transform_types must not be empty")

        for name in (
            "value_range",
            "list_length_range",
            "threshold_range",
            "divisor_range",
            "shift_range",
            "scale_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        lo, hi = self.list_length_range
        if lo < 0:
            raise ValueError(f"list_length_range: low ({lo}) must be >= 0")

        lo, hi = self.divisor_range
        if lo < 1:
            raise ValueError(f"divisor_range: low ({lo}) must be >= 1")

        has_boolean_composition = (
            PredicateType.AND in self.predicate_types
            or PredicateType.OR in self.predicate_types
        )
        if has_boolean_composition and self.min_composed_operands > 3:
            raise ValueError(
                "min_composed_operands must be <= 3 when AND/OR predicates "
                "are enabled"
            )

        return self
