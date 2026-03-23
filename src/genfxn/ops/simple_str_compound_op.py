from __future__ import annotations

from typing import Literal

from pydantic import Field

from genfxn.ops.compound_op import CompoundOp
from genfxn.spaces.simple_str_compound_space import SimpleStrCompoundSpace
from genfxn.spaces.simple_string_input_space import SimpleStringInputSpace
from genfxn.spaces.string_space import StringSpace


class SimpleStrCompoundOp(CompoundOp):
    """Compound op for simple parameter-free string transforms."""

    op_type: Literal["simple_str_compound"] = "simple_str_compound"
    transform: str
    transform_space: SimpleStrCompoundSpace = Field(  # type: ignore[assignment]
        default_factory=SimpleStrCompoundSpace
    )
    input_space: StringSpace = Field(  # type: ignore[assignment]
        default_factory=SimpleStringInputSpace,
    )
