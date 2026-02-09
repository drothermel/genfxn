from enum import Enum

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


class IntervalsSpec(BaseModel):
    operation: OperationType
    boundary_mode: BoundaryMode
    merge_touching: bool


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
    allow_reversed_interval_prob_range: tuple[float, float] = Field(
        default=(0.0, 0.3)
    )
    degenerate_interval_prob_range: tuple[float, float] = Field(
        default=(0.0, 0.3)
    )
    nested_interval_prob_range: tuple[float, float] = Field(
        default=(0.0, 0.3)
    )

    @model_validator(mode="after")
    def validate_axes(self) -> "IntervalsAxes":
        if not self.operation_types:
            raise ValueError("operation_types must not be empty")
        if not self.boundary_modes:
            raise ValueError("boundary_modes must not be empty")
        if not self.merge_touching_choices:
            raise ValueError("merge_touching_choices must not be empty")

        for name in ("n_intervals_range", "endpoint_range", "max_span_range"):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.n_intervals_range[0] < 0:
            raise ValueError("n_intervals_range: low must be >= 0")
        if self.max_span_range[0] < 0:
            raise ValueError("max_span_range: low must be >= 0")

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
