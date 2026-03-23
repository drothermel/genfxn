from __future__ import annotations

from typing import Literal, get_args

from pydantic import Field

from genfxn.spaces.categorical_space import CategoricalSpace

SimpleStrCompoundType = Literal[
    "lower_str",
    "upper_str",
    "capitalize_str",
    "swapcase_str",
    "reverse_str",
    "casefold_str",
    "title_str",
    "strip_str",
    "lstrip_str",
    "rstrip_str",
    "expandtabs_str",
]

_SIMPLE_STR_COMPOUND_VALUES: tuple[SimpleStrCompoundType, ...] = get_args(
    SimpleStrCompoundType
)


class SimpleStrCompoundSpace(CategoricalSpace):
    """Categorical space over leaf string op_type values."""

    values: tuple[SimpleStrCompoundType, ...] = Field(  # type: ignore[assignment]
        default=_SIMPLE_STR_COMPOUND_VALUES
    )
