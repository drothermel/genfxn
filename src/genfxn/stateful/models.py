from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from genfxn.core.int64_safety import (
    abs_range,
    add_ranges,
    fits_signed_i64,
    mul_ranges,
    neg_range,
)
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
INT32_MAX = (1 << 31) - 1
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1
SAMPLED_INIT_RANGE = (-10, 10)
_SUPPORTED_STATEFUL_TRANSFORM_TYPES = frozenset(
    {
        TransformType.IDENTITY,
        TransformType.ABS,
        TransformType.SHIFT,
        TransformType.NEGATE,
        TransformType.SCALE,
        TransformType.PIPELINE,
    }
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


def _range_includes_int64_min(value_range: tuple[int, int]) -> bool:
    lo, hi = value_range
    return lo <= INT64_MIN <= hi


def _apply_transform_range(
    input_range: tuple[int, int],
    transform_type: TransformType,
    *,
    shift_range: tuple[int, int],
    scale_range: tuple[int, int],
) -> tuple[int, int]:
    if transform_type == TransformType.IDENTITY:
        output_range = input_range
    elif transform_type == TransformType.ABS:
        if _range_includes_int64_min(input_range):
            raise ValueError(
                "Numeric contract violation: transform composition can route "
                "INT64_MIN into ABS, which is overflow-unsafe across runtimes. "
                "Tighten ranges."
            )
        output_range = abs_range(input_range)
    elif transform_type == TransformType.SHIFT:
        output_range = add_ranges(input_range, shift_range)
    elif transform_type == TransformType.NEGATE:
        if _range_includes_int64_min(input_range):
            raise ValueError(
                "Numeric contract violation: transform composition can route "
                "INT64_MIN into NEGATE, which is overflow-unsafe across "
                "runtimes. Tighten ranges."
            )
        output_range = neg_range(input_range)
    elif transform_type == TransformType.SCALE:
        output_range = mul_ranges(input_range, scale_range)
    else:  # pragma: no cover - guarded by caller
        output_range = input_range

    if not fits_signed_i64(output_range):
        raise ValueError(
            "Numeric contract violation: value_range, shift_range, and "
            "scale_range must keep transform outputs within signed 64-bit "
            "bounds"
        )
    return output_range


def _pipeline_output_ranges(
    base_range: tuple[int, int],
    *,
    shift_range: tuple[int, int],
    scale_range: tuple[int, int],
) -> list[tuple[int, int]]:
    """Compute all output ranges for sampled numeric pipelines.

    Stateful pipeline sampling is fixed to:
    - first step in {SHIFT, SCALE}
    - total length in {2, 3}
    - remaining steps in {SHIFT, SCALE, ABS, NEGATE}
    """
    first_step_types = (TransformType.SHIFT, TransformType.SCALE)
    rest_step_types = (
        TransformType.SHIFT,
        TransformType.SCALE,
        TransformType.ABS,
        TransformType.NEGATE,
    )

    def _expand(
        input_range: tuple[int, int], steps_remaining: int
    ) -> list[tuple[int, int]]:
        if steps_remaining == 0:
            return [input_range]

        outputs: list[tuple[int, int]] = []
        for step_type in rest_step_types:
            next_range = _apply_transform_range(
                input_range,
                step_type,
                shift_range=shift_range,
                scale_range=scale_range,
            )
            outputs.extend(_expand(next_range, steps_remaining - 1))
        return outputs

    output_ranges: list[tuple[int, int]] = []
    for first_step in first_step_types:
        first_range = _apply_transform_range(
            base_range,
            first_step,
            shift_range=shift_range,
            scale_range=scale_range,
        )
        output_ranges.extend(_expand(first_range, 1))
        output_ranges.extend(_expand(first_range, 2))
    return output_ranges


class TemplateType(str, Enum):
    CONDITIONAL_LINEAR_SUM = "conditional_linear_sum"
    RESETTING_BEST_PREFIX_SUM = "resetting_best_prefix_sum"
    LONGEST_RUN = "longest_run"
    TOGGLE_SUM = "toggle_sum"


_TRANSFORMED_TEMPLATES = frozenset(
    {
        TemplateType.CONDITIONAL_LINEAR_SUM,
        TemplateType.RESETTING_BEST_PREFIX_SUM,
        TemplateType.TOGGLE_SUM,
    }
)


# --- Template Specs ---


class ConditionalLinearSumSpec(BaseModel):
    template: Literal["conditional_linear_sum"] = "conditional_linear_sum"
    predicate: Predicate
    true_transform: Transform
    false_transform: Transform
    init_value: int = Field(default=0, ge=INT64_MIN, le=INT64_MAX)


class ResettingBestPrefixSumSpec(BaseModel):
    template: Literal["resetting_best_prefix_sum"] = "resetting_best_prefix_sum"
    reset_predicate: Predicate
    init_value: int = Field(default=0, ge=INT64_MIN, le=INT64_MAX)
    value_transform: Transform | None = None


class LongestRunSpec(BaseModel):
    template: Literal["longest_run"] = "longest_run"
    match_predicate: Predicate


class ToggleSumSpec(BaseModel):
    template: Literal["toggle_sum"] = "toggle_sum"
    toggle_predicate: Predicate
    on_transform: Transform
    off_transform: Transform
    init_value: int = Field(default=0, ge=INT64_MIN, le=INT64_MAX)


StatefulSpec = Annotated[
    ConditionalLinearSumSpec
    | ResettingBestPrefixSumSpec
    | LongestRunSpec
    | ToggleSumSpec,
    Field(discriminator="template"),
]


# --- Axes (sampling configuration) ---


class StatefulAxes(BaseModel):
    """Sampling constraints for generated-spec parity across runtimes.

    Contract scope: generated specs/tasks under validated axes only.
    Hand-authored specs outside these constraints are not parity-covered.
    """

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
            if lo < INT64_MIN:
                raise ValueError(f"{name}: low ({lo}) must be >= {INT64_MIN}")
            if hi > INT64_MAX:
                raise ValueError(f"{name}: high ({hi}) must be <= {INT64_MAX}")

        lo, hi = self.list_length_range
        if lo < 0:
            raise ValueError(f"list_length_range: low ({lo}) must be >= 0")

        lo, hi = self.divisor_range
        if lo < 1:
            raise ValueError(f"divisor_range: low ({lo}) must be >= 1")
        if hi > INT32_MAX:
            raise ValueError(
                f"divisor_range: high ({hi}) must be <= {INT32_MAX}"
            )

        has_boolean_composition = (
            PredicateType.AND in self.predicate_types
            or PredicateType.OR in self.predicate_types
        )
        if has_boolean_composition and self.min_composed_operands > 3:
            raise ValueError(
                "min_composed_operands must be <= 3 when AND/OR predicates "
                "are enabled"
            )

        uses_transforms = any(
            template in _TRANSFORMED_TEMPLATES for template in self.templates
        )
        if not uses_transforms:
            return self

        unsupported_transform_types = sorted(
            set(self.transform_types) - _SUPPORTED_STATEFUL_TRANSFORM_TYPES,
            key=lambda transform_type: transform_type.value,
        )
        if unsupported_transform_types:
            unsupported = ", ".join(
                transform_type.value
                for transform_type in unsupported_transform_types
            )
            supported = ", ".join(
                transform_type.value
                for transform_type in sorted(
                    _SUPPORTED_STATEFUL_TRANSFORM_TYPES,
                    key=lambda transform_type: transform_type.value,
                )
            )
            raise ValueError(
                "transform_types contains unsupported values for "
                f"stateful generation: {unsupported}. "
                f"Supported values: {supported}"
            )

        if (
            TransformType.SHIFT in self.transform_types
            or TransformType.PIPELINE in self.transform_types
        ) and self.shift_range[0] == INT64_MIN:
            raise ValueError(
                "shift_range: low must be > INT64_MIN when SHIFT transforms "
                "are enabled"
            )

        value_range = self.value_range
        transform_output_ranges: list[tuple[int, int]] = []
        for transform_type in self.transform_types:
            if transform_type == TransformType.IDENTITY:
                output_range = _apply_transform_range(
                    value_range,
                    transform_type,
                    shift_range=self.shift_range,
                    scale_range=self.scale_range,
                )
                transform_output_ranges.append(output_range)
            elif transform_type == TransformType.ABS:
                if value_range[0] == INT64_MIN:
                    raise ValueError(
                        "value_range: low must be > INT64_MIN when ABS "
                        "transforms are enabled"
                    )
                output_range = _apply_transform_range(
                    value_range,
                    transform_type,
                    shift_range=self.shift_range,
                    scale_range=self.scale_range,
                )
                transform_output_ranges.append(output_range)
            elif transform_type == TransformType.SHIFT:
                output_range = _apply_transform_range(
                    value_range,
                    transform_type,
                    shift_range=self.shift_range,
                    scale_range=self.scale_range,
                )
                transform_output_ranges.append(output_range)
            elif transform_type == TransformType.NEGATE:
                if value_range[0] == INT64_MIN:
                    raise ValueError(
                        "value_range: low must be > INT64_MIN when NEGATE "
                        "transforms are enabled"
                    )
                output_range = _apply_transform_range(
                    value_range,
                    transform_type,
                    shift_range=self.shift_range,
                    scale_range=self.scale_range,
                )
                transform_output_ranges.append(output_range)
            elif transform_type == TransformType.SCALE:
                output_range = _apply_transform_range(
                    value_range,
                    transform_type,
                    shift_range=self.shift_range,
                    scale_range=self.scale_range,
                )
                transform_output_ranges.append(output_range)
            elif transform_type == TransformType.PIPELINE:
                transform_output_ranges.extend(
                    _pipeline_output_ranges(
                        value_range,
                        shift_range=self.shift_range,
                        scale_range=self.scale_range,
                    )
                )
            else:  # pragma: no cover - guarded above
                continue

        if not transform_output_ranges:
            return self

        merged_transform_range = (
            min(bounds[0] for bounds in transform_output_ranges),
            max(bounds[1] for bounds in transform_output_ranges),
        )
        step_count = self.list_length_range[1]
        acc_range = add_ranges(
            SAMPLED_INIT_RANGE,
            (
                step_count * merged_transform_range[0],
                step_count * merged_transform_range[1],
            ),
        )
        if not fits_signed_i64(acc_range):
            raise ValueError(
                "Numeric contract violation: list_length_range and transform "
                "ranges can overflow signed 64-bit accumulator math. "
                "Tighten ranges."
            )

        return self
