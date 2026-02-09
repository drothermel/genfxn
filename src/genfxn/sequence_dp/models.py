from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class TemplateType(str, Enum):
    GLOBAL = "global"
    LOCAL = "local"


class OutputMode(str, Enum):
    SCORE = "score"
    ALIGNMENT_LEN = "alignment_len"
    GAP_COUNT = "gap_count"


class PredicateType(str, Enum):
    EQ = "eq"
    ABS_DIFF_LE = "abs_diff_le"
    MOD_EQ = "mod_eq"


class TieBreakOrder(str, Enum):
    DIAG_UP_LEFT = "diag_up_left"
    DIAG_LEFT_UP = "diag_left_up"
    UP_DIAG_LEFT = "up_diag_left"
    UP_LEFT_DIAG = "up_left_diag"
    LEFT_DIAG_UP = "left_diag_up"
    LEFT_UP_DIAG = "left_up_diag"


class PredicateEq(BaseModel):
    kind: Literal["eq"] = "eq"


class PredicateAbsDiffLe(BaseModel):
    kind: Literal["abs_diff_le"] = "abs_diff_le"
    max_diff: int = Field(ge=0)


class PredicateModEq(BaseModel):
    kind: Literal["mod_eq"] = "mod_eq"
    divisor: int = Field(ge=1)
    remainder: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_remainder(self) -> "PredicateModEq":
        if self.remainder >= self.divisor:
            raise ValueError("remainder must be < divisor")
        return self


SequenceDpPredicate = Annotated[
    PredicateEq | PredicateAbsDiffLe | PredicateModEq,
    Field(discriminator="kind"),
]


class SequenceDpSpec(BaseModel):
    template: TemplateType
    output_mode: OutputMode
    match_predicate: SequenceDpPredicate
    match_score: int
    mismatch_score: int
    gap_score: int
    step_tie_break: TieBreakOrder


class SequenceDpAxes(BaseModel):
    target_difficulty: int | None = Field(default=None, ge=1, le=5)
    templates: list[TemplateType] = Field(
        default_factory=lambda: list(TemplateType)
    )
    output_modes: list[OutputMode] = Field(
        default_factory=lambda: list(OutputMode)
    )
    predicate_types: list[PredicateType] = Field(
        default_factory=lambda: list(PredicateType)
    )
    len_a_range: tuple[int, int] = Field(default=(2, 10))
    len_b_range: tuple[int, int] = Field(default=(2, 10))
    value_range: tuple[int, int] = Field(default=(-20, 20))
    match_score_range: tuple[int, int] = Field(default=(1, 6))
    mismatch_score_range: tuple[int, int] = Field(default=(-4, 1))
    gap_score_range: tuple[int, int] = Field(default=(-4, 0))
    abs_diff_range: tuple[int, int] = Field(default=(0, 5))
    divisor_range: tuple[int, int] = Field(default=(1, 10))
    tie_break_orders: list[TieBreakOrder] = Field(
        default_factory=lambda: list(TieBreakOrder)
    )

    @model_validator(mode="after")
    def validate_axes(self) -> "SequenceDpAxes":
        if not self.templates:
            raise ValueError("templates must not be empty")
        if not self.output_modes:
            raise ValueError("output_modes must not be empty")
        if not self.predicate_types:
            raise ValueError("predicate_types must not be empty")
        if not self.tie_break_orders:
            raise ValueError("tie_break_orders must not be empty")

        for name in (
            "len_a_range",
            "len_b_range",
            "value_range",
            "match_score_range",
            "mismatch_score_range",
            "gap_score_range",
            "abs_diff_range",
            "divisor_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.len_a_range[0] < 0:
            raise ValueError("len_a_range: low must be >= 0")
        if self.len_b_range[0] < 0:
            raise ValueError("len_b_range: low must be >= 0")
        if self.abs_diff_range[0] < 0:
            raise ValueError("abs_diff_range: low must be >= 0")
        if self.divisor_range[0] < 1:
            raise ValueError("divisor_range: low must be >= 1")

        return self
