from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class OperationType(str, Enum):
    TOTAL_COVERAGE = "total_coverage"
    MERGED_COUNT = "merged_count"
    MAX_OVERLAP_COUNT = "max_overlap_count"
    GAP_COUNT = "gap_count"


class BoundaryMode(str, Enum):
    CLOSED_CLOSED = "closed_closed"
    CLOSED_OPEN = "closed_open"
    OPEN_CLOSED = "open_closed"
    OPEN_OPEN = "open_open"


_INT_RANGE_FIELDS = (
    "n_intervals_range",
    "endpoint_range",
    "max_span_range",
    "endpoint_clip_abs_range",
    "endpoint_quantize_step_range",
)
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1


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


class IntervalsSpec(BaseModel):
    operation: OperationType
    boundary_mode: BoundaryMode
    merge_touching: bool
    endpoint_clip_abs: int = Field(default=20, ge=1, le=INT64_MAX)
    endpoint_quantize_step: int = Field(default=1, ge=1, le=INT64_MAX)
    allow_reversed_interval_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    degenerate_interval_prob: float = Field(default=0.0, ge=0.0, le=1.0)
    nested_interval_prob: float = Field(default=0.0, ge=0.0, le=1.0)


class IntervalsAxes(BaseModel):
    target_difficulty: int | None = Field(default=None, ge=1, le=5)
    operation_types: list[OperationType] = Field(
        default_factory=lambda: list(OperationType)
    )
    boundary_modes: list[BoundaryMode] = Field(
        default_factory=lambda: list(BoundaryMode)
    )
    merge_touching_choices: list[bool] = Field(
        default_factory=lambda: [False, True]
    )
    n_intervals_range: tuple[int, int] = Field(default=(0, 10))
    endpoint_range: tuple[int, int] = Field(default=(-20, 20))
    max_span_range: tuple[int, int] = Field(default=(0, 20))
    endpoint_clip_abs_range: tuple[int, int] = Field(default=(3, 20))
    endpoint_quantize_step_range: tuple[int, int] = Field(default=(1, 4))
    allow_reversed_interval_prob_range: tuple[float, float] = Field(
        default=(0.0, 0.3)
    )
    degenerate_interval_prob_range: tuple[float, float] = Field(
        default=(0.0, 0.3)
    )
    nested_interval_prob_range: tuple[float, float] = Field(default=(0.0, 0.3))

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "IntervalsAxes":
        if not self.operation_types:
            raise ValueError("operation_types must not be empty")
        if not self.boundary_modes:
            raise ValueError("boundary_modes must not be empty")
        if not self.merge_touching_choices:
            raise ValueError("merge_touching_choices must not be empty")

        for name in (
            "n_intervals_range",
            "endpoint_range",
            "max_span_range",
            "endpoint_clip_abs_range",
            "endpoint_quantize_step_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.n_intervals_range[0] < 0:
            raise ValueError("n_intervals_range: low must be >= 0")
        if self.max_span_range[0] < 0:
            raise ValueError("max_span_range: low must be >= 0")
        if self.endpoint_clip_abs_range[0] < 1:
            raise ValueError("endpoint_clip_abs_range: low must be >= 1")
        if self.endpoint_quantize_step_range[0] < 1:
            raise ValueError("endpoint_quantize_step_range: low must be >= 1")
        if self.endpoint_range[0] < INT64_MIN:
            raise ValueError(f"endpoint_range: low must be >= {INT64_MIN}")
        if self.endpoint_range[1] > INT64_MAX:
            raise ValueError(f"endpoint_range: high must be <= {INT64_MAX}")
        if self.max_span_range[1] > INT64_MAX:
            raise ValueError(f"max_span_range: high must be <= {INT64_MAX}")
        if self.endpoint_clip_abs_range[1] > INT64_MAX:
            raise ValueError(
                f"endpoint_clip_abs_range: high must be <= {INT64_MAX}"
            )
        if self.endpoint_quantize_step_range[1] > INT64_MAX:
            raise ValueError(
                f"endpoint_quantize_step_range: high must be <= {INT64_MAX}"
            )

        for name in (
            "allow_reversed_interval_prob_range",
            "degenerate_interval_prob_range",
            "nested_interval_prob_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")
            if lo < 0.0 or hi > 1.0:
                raise ValueError(f"{name}: values must be in [0.0, 1.0]")

        return self
