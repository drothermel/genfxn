from __future__ import annotations

from typing import Literal, get_args

from pydantic import Field

from genfxn.spaces.categorical_space import CategoricalSpace

SimpleStrTransformType = Literal[
    "lowercase",
    "uppercase",
    "capitalize",
    "swapcase",
    "reverse",
    "casefold",
    "title",
    "strip",
    "lstrip",
    "rstrip",
    "expandtabs",
]

_SIMPLE_STR_TRANSFORM_VALUES: tuple[SimpleStrTransformType, ...] = get_args(
    SimpleStrTransformType
)


class SimpleStrTransformSpace(CategoricalSpace):
    """Hardcoded categorical space for parameter-free string transforms."""

    values: tuple[SimpleStrTransformType, ...] = Field(  # type: ignore[assignment]
        default=_SIMPLE_STR_TRANSFORM_VALUES
    )
