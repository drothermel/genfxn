from __future__ import annotations

from typing import Literal, get_args

from pydantic import Field

from genfxn.param_space import CategoricalParamSpace

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


class SimpleStrTransformSpace(CategoricalParamSpace):
    """Hardcoded categorical space for parameter-free string transforms."""

    values: tuple[SimpleStrTransformType, ...] = Field(
        default=_SIMPLE_STR_TRANSFORM_VALUES
    )
