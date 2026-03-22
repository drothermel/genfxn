from __future__ import annotations

import string
from typing import Any, Literal, cast

from pydantic import Field

from genfxn.ops.compound_op import CompoundOp
from genfxn.spaces.categorical_space import CategoricalSpace
from genfxn.spaces.char_style_transform_space import (
    CharStyleTransformSpace,
    CharStyleTransformType,
)
from genfxn.types import DEFAULT_STR_INPUT_VAR


def _lower_alpha_input_space() -> CategoricalSpace:
    return CategoricalSpace(values=tuple(string.ascii_lowercase))


class CharStyleCompoundOp(CompoundOp):
    """Compound op for transforming a lowercase char to lower/upper/tab."""

    op_type: Literal["char_style_transform"] = "char_style_transform"
    transform: CharStyleTransformType
    transform_space: CharStyleTransformSpace = Field(
        default_factory=CharStyleTransformSpace
    )
    input_space: CategoricalSpace = Field(  # type: ignore[assignment]
        default_factory=_lower_alpha_input_space
    )
    input_var: str = "ch"

    def eval(self, **kwargs: Any) -> str:
        self.validate_input(**kwargs)
        input = cast(str, kwargs[DEFAULT_STR_INPUT_VAR])
        match self.transform:
            case "upper":
                return input.upper()
            case "lower":
                return input.lower()
            case "tab":
                return "\t"
        raise AssertionError("unreachable transform")

    def render_python(self) -> str:
        v = self.input_var
        match self.transform:
            case "upper":
                return f"{v}.upper()"
            case "lower":
                return f"{v}.lower()"
            case "tab":
                return r"'\t'"
        raise AssertionError("unreachable transform")
