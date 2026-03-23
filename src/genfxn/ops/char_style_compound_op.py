from __future__ import annotations

import string
from typing import Literal

from pydantic import Field

from genfxn.ops.compound_op import CompoundOp
from genfxn.spaces.categorical_space import CategoricalSpace
from genfxn.spaces.char_style_compound_space import (
    CharStyleCompoundSpace,
    CharStyleCompoundType,
)


def _lower_alpha_input_space() -> CategoricalSpace:
    return CategoricalSpace(values=tuple(string.ascii_lowercase))


class CharStyleCompoundOp(CompoundOp):
    """Compound op for char-style transforms (upper/lower/tab)."""

    op_type: Literal["char_style_compound"] = "char_style_compound"
    transform: CharStyleCompoundType
    transform_space: CharStyleCompoundSpace = Field(  # type: ignore[assignment]
        default_factory=CharStyleCompoundSpace
    )
    input_space: CategoricalSpace = Field(  # type: ignore[assignment]
        default_factory=_lower_alpha_input_space
    )
