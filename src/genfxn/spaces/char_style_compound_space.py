from __future__ import annotations

from typing import Literal, cast, get_args

from pydantic import Field

from genfxn.spaces.categorical_space import CategoricalSpace

CharStyleCompoundType = Literal["upper_str", "lower_str", "tab_str"]

_CHAR_STYLE_COMPOUND_VALUES: tuple[CharStyleCompoundType, ...] = cast(
    tuple[CharStyleCompoundType, ...],
    get_args(CharStyleCompoundType),
)


class CharStyleCompoundSpace(CategoricalSpace):
    """Categorical space over char-style leaf op_type values."""

    values: tuple[CharStyleCompoundType, ...] = Field(
        default=_CHAR_STYLE_COMPOUND_VALUES
    )
