from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class PredicateKind(str, Enum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"


class TemporalOperator(str, Enum):
    ATOM = "atom"
    NOT = "not"
    AND = "and"
    OR = "or"
    NEXT = "next"
    EVENTUALLY = "eventually"
    ALWAYS = "always"
    UNTIL = "until"
    SINCE = "since"


class TemporalOutputMode(str, Enum):
    SAT_AT_START = "sat_at_start"
    SAT_COUNT = "sat_count"
    FIRST_SAT_INDEX = "first_sat_index"


_UNARY_OPERATORS = frozenset(
    {
        TemporalOperator.NOT,
        TemporalOperator.NEXT,
        TemporalOperator.EVENTUALLY,
        TemporalOperator.ALWAYS,
    }
)
_BINARY_OPERATORS = frozenset(
    {
        TemporalOperator.AND,
        TemporalOperator.OR,
        TemporalOperator.UNTIL,
        TemporalOperator.SINCE,
    }
)
_INT_RANGE_FIELDS = (
    "formula_depth_range",
    "sequence_length_range",
    "value_range",
    "predicate_constant_range",
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


def _validate_formula_node(node: Any) -> int:
    if not isinstance(node, dict):
        raise ValueError("formula node must be a dict")
    raw_op = node.get("op")
    if not isinstance(raw_op, str):
        raise ValueError("formula node is missing string field 'op'")
    try:
        op = TemporalOperator(raw_op)
    except ValueError as exc:
        raise ValueError(f"unknown operator '{raw_op}'") from exc

    if op == TemporalOperator.ATOM:
        raw_predicate = node.get("predicate")
        if not isinstance(raw_predicate, str):
            raise ValueError("atom node must include string 'predicate'")
        try:
            PredicateKind(raw_predicate)
        except ValueError as exc:
            raise ValueError(
                f"unknown predicate kind '{raw_predicate}'"
            ) from exc
        constant = node.get("constant")
        if type(constant) is not int:
            raise ValueError("atom node must include int 'constant'")
        if constant < INT64_MIN or constant > INT64_MAX:
            raise ValueError(
                f"atom node constant must be in [{INT64_MIN}, {INT64_MAX}]"
            )
        return 1

    if op in _UNARY_OPERATORS:
        if "child" not in node:
            raise ValueError(f"{op.value} node must include 'child'")
        return 1 + _validate_formula_node(node["child"])

    if op in _BINARY_OPERATORS:
        if "left" not in node or "right" not in node:
            raise ValueError(f"{op.value} node must include 'left' and 'right'")
        left_depth = _validate_formula_node(node["left"])
        right_depth = _validate_formula_node(node["right"])
        return 1 + max(left_depth, right_depth)

    raise ValueError(f"unsupported operator '{op.value}'")


class TemporalLogicSpec(BaseModel):
    output_mode: TemporalOutputMode = TemporalOutputMode.SAT_AT_START
    formula: dict[str, Any]

    @model_validator(mode="after")
    def validate_spec(self) -> TemporalLogicSpec:
        depth = _validate_formula_node(self.formula)
        if depth > 12:
            raise ValueError("formula depth must be <= 12")
        return self


class TemporalLogicAxes(BaseModel):
    target_difficulty: int | None = Field(default=None, ge=1, le=5)
    output_modes: list[TemporalOutputMode] = Field(
        default_factory=lambda: list(TemporalOutputMode)
    )
    formula_depth_range: tuple[int, int] = Field(default=(1, 3))
    operator_mix: list[TemporalOperator] = Field(
        default_factory=lambda: list(TemporalOperator)
    )
    include_since_choices: list[bool] = Field(
        default_factory=lambda: [False, True]
    )
    sequence_length_range: tuple[int, int] = Field(default=(0, 10))
    value_range: tuple[int, int] = Field(default=(-10, 10))
    predicate_constant_range: tuple[int, int] = Field(default=(-8, 8))

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> TemporalLogicAxes:
        if not self.output_modes:
            raise ValueError("output_modes must not be empty")
        if not self.operator_mix:
            raise ValueError("operator_mix must not be empty")
        if not self.include_since_choices:
            raise ValueError("include_since_choices must not be empty")

        for name in (
            "formula_depth_range",
            "sequence_length_range",
            "value_range",
            "predicate_constant_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.formula_depth_range[0] < 1:
            raise ValueError("formula_depth_range: low must be >= 1")
        if self.formula_depth_range[1] > 12:
            raise ValueError("formula_depth_range: high must be <= 12")
        if self.sequence_length_range[0] < 0:
            raise ValueError("sequence_length_range: low must be >= 0")
        for name in ("value_range", "predicate_constant_range"):
            lo, hi = getattr(self, name)
            if lo < INT64_MIN:
                raise ValueError(f"{name}: low must be >= {INT64_MIN}")
            if hi > INT64_MAX:
                raise ValueError(f"{name}: high must be <= {INT64_MAX}")

        return self
