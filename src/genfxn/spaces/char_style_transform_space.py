from __future__ import annotations

from typing import Literal, cast, get_args

from pydantic import Field

from genfxn.spaces.categorical_space import CategoricalSpace

CharStyleTransformType = Literal["upper", "lower", "tab"]

_CHAR_STYLE_TRANSFORM_VALUES: tuple[CharStyleTransformType, ...] = cast(
    tuple[CharStyleTransformType, ...],
    get_args(CharStyleTransformType),
)


class CharStyleTransformSpace(CategoricalSpace):
    """Categorical space for char-style transform operations."""

    values: tuple[CharStyleTransformType, ...] = Field(
        default=_CHAR_STYLE_TRANSFORM_VALUES
    )
