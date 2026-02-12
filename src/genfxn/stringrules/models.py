from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from genfxn.core.string_predicates import StringPredicate, StringPredicateType
from genfxn.core.string_transforms import StringTransform, StringTransformType
from genfxn.stringrules.utils import _get_charset

_INT_RANGE_FIELDS = (
    "string_length_range",
    "prefix_suffix_length_range",
    "substring_length_range",
    "length_threshold_range",
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


class OverlapLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    HIGH = "high"


class StringRule(BaseModel):
    predicate: StringPredicate
    transform: StringTransform


class StringRulesSpec(BaseModel):
    rules: list[StringRule]
    default_transform: StringTransform


class StringRulesAxes(BaseModel):
    n_rules: int = Field(default=3, ge=1, le=10)
    predicate_types: list[StringPredicateType] = Field(
        default_factory=lambda: [
            StringPredicateType.STARTS_WITH,
            StringPredicateType.ENDS_WITH,
            StringPredicateType.CONTAINS,
            StringPredicateType.IS_ALPHA,
            StringPredicateType.IS_DIGIT,
            StringPredicateType.IS_UPPER,
            StringPredicateType.IS_LOWER,
            StringPredicateType.LENGTH_CMP,
        ]
    )
    transform_types: list[StringTransformType] = Field(
        default_factory=lambda: [
            StringTransformType.IDENTITY,
            StringTransformType.LOWERCASE,
            StringTransformType.UPPERCASE,
            StringTransformType.CAPITALIZE,
            StringTransformType.SWAPCASE,
            StringTransformType.REVERSE,
            StringTransformType.REPLACE,
            StringTransformType.STRIP,
            StringTransformType.PREPEND,
            StringTransformType.APPEND,
        ]
    )
    overlap_level: OverlapLevel = Field(default=OverlapLevel.LOW)
    string_length_range: tuple[int, int] = Field(default=(1, 20))
    charset: str = Field(default="ascii_letters_digits")
    prefix_suffix_length_range: tuple[int, int] = Field(default=(1, 4))
    substring_length_range: tuple[int, int] = Field(default=(1, 3))
    length_threshold_range: tuple[int, int] = Field(default=(1, 15))

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "StringRulesAxes":
        if not self.predicate_types:
            raise ValueError("predicate_types must not be empty")
        if not self.transform_types:
            raise ValueError("transform_types must not be empty")
        resolved_charset = _get_charset(self.charset)
        if not resolved_charset:
            raise ValueError(
                "charset must resolve to a non-empty character set"
            )
        if any(ord(ch) > 127 for ch in resolved_charset):
            raise ValueError("charset must be ASCII-only for parity")

        for name in (
            "string_length_range",
            "prefix_suffix_length_range",
            "substring_length_range",
            "length_threshold_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")
            if lo < 0:
                raise ValueError(f"{name}: low ({lo}) must be >= 0")

        return self
