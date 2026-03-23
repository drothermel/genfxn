from __future__ import annotations

import string
from typing import Literal

from pydantic import Field

from genfxn.ops.compound_op import CompoundOp
from genfxn.spaces.char_space import CharSpace
from genfxn.spaces.char_style_compound_space import CharStyleCompoundSpace


def _lower_alpha_char_space() -> CharSpace:
    return CharSpace(values=tuple(string.ascii_lowercase))


class CharStyleCompoundOp(CompoundOp):
    """Compound op for char-style transforms (upper/lower/tab)."""

    op_type: Literal["char_style_compound"] = "char_style_compound"
    transform: str
    transform_space: CharStyleCompoundSpace = Field(  # type: ignore[assignment]
        default_factory=CharStyleCompoundSpace
    )
    input_space: CharSpace = Field(  # type: ignore[assignment]
        default_factory=_lower_alpha_char_space
    )
