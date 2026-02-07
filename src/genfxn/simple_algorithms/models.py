from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from genfxn.core.predicates import Predicate, PredicateType
from genfxn.core.transforms import Transform, TransformType


class TemplateType(str, Enum):
    MOST_FREQUENT = "most_frequent"
    COUNT_PAIRS_SUM = "count_pairs_sum"
    MAX_WINDOW_SUM = "max_window_sum"


class TieBreakMode(str, Enum):
    SMALLEST = "smallest"
    FIRST_SEEN = "first_seen"


class CountingMode(str, Enum):
    ALL_INDICES = "all_indices"
    UNIQUE_VALUES = "unique_values"


class MostFrequentSpec(BaseModel):
    template: Literal["most_frequent"] = "most_frequent"
    tie_break: TieBreakMode
    empty_default: int = 0
    pre_filter: Predicate | None = None
    pre_transform: Transform | None = None
    tie_default: int | None = None


class CountPairsSumSpec(BaseModel):
    template: Literal["count_pairs_sum"] = "count_pairs_sum"
    target: int
    counting_mode: CountingMode
    pre_filter: Predicate | None = None
    pre_transform: Transform | None = None
    no_result_default: int | None = None
    short_list_default: int | None = None


class MaxWindowSumSpec(BaseModel):
    template: Literal["max_window_sum"] = "max_window_sum"
    k: int
    invalid_k_default: int = 0
    pre_filter: Predicate | None = None
    pre_transform: Transform | None = None
    empty_default: int | None = None

    @model_validator(mode="after")
    def validate_k(self) -> "MaxWindowSumSpec":
        if self.k < 1:
            raise ValueError(f"k must be >= 1, got {self.k}")
        return self


SimpleAlgorithmsSpec = Annotated[
    MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec,
    Field(discriminator="template"),
]


class SimpleAlgorithmsAxes(BaseModel):
    templates: list[TemplateType] = Field(
        default_factory=lambda: list(TemplateType)
    )
    tie_break_modes: list[TieBreakMode] = Field(
        default_factory=lambda: list(TieBreakMode)
    )
    counting_modes: list[CountingMode] = Field(
        default_factory=lambda: list(CountingMode)
    )
    value_range: tuple[int, int] = Field(default=(-100, 100))
    list_length_range: tuple[int, int] = Field(default=(5, 20))
    target_range: tuple[int, int] = Field(default=(-50, 50))
    window_size_range: tuple[int, int] = Field(default=(1, 10))
    empty_default_range: tuple[int, int] = Field(default=(0, 0))
    pre_filter_types: list[PredicateType] | None = None
    pre_transform_types: list[TransformType] | None = None
    tie_default_range: tuple[int, int] | None = None
    no_result_default_range: tuple[int, int] | None = None
    short_list_default_range: tuple[int, int] | None = None
    empty_default_for_empty_range: tuple[int, int] | None = None

    @model_validator(mode="after")
    def validate_axes(self) -> "SimpleAlgorithmsAxes":
        if not self.templates:
            raise ValueError("templates must not be empty")
        if not self.tie_break_modes:
            raise ValueError("tie_break_modes must not be empty")
        if not self.counting_modes:
            raise ValueError("counting_modes must not be empty")

        for name in (
            "value_range",
            "list_length_range",
            "target_range",
            "window_size_range",
            "empty_default_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        lo, hi = self.list_length_range
        if lo < 0:
            raise ValueError(f"list_length_range: low ({lo}) must be >= 0")

        lo, hi = self.window_size_range
        if lo < 1:
            raise ValueError(f"window_size_range: low ({lo}) must be >= 1")

        if self.pre_filter_types is not None and not self.pre_filter_types:
            raise ValueError(
                "pre_filter_types must not be empty when provided"
            )
        if (
            self.pre_transform_types is not None
            and not self.pre_transform_types
        ):
            raise ValueError(
                "pre_transform_types must not be empty when provided"
            )

        return self
