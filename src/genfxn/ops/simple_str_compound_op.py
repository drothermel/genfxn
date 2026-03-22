from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field

from genfxn.ops.compound_op import CompoundOp
from genfxn.spaces.simple_str_transform_space import (
    SimpleStrTransformSpace,
    SimpleStrTransformType,
)
from genfxn.spaces.simple_string_input_space import SimpleStringInputSpace
from genfxn.spaces.string_space import StringSpace
from genfxn.types import DEFAULT_STR_INPUT_VAR


class SimpleStrCompoundOp(CompoundOp):
    """Compound op for simple parameter-free string transforms."""

    op_type: Literal["simple_str_transform"] = "simple_str_transform"
    transform: SimpleStrTransformType
    transform_space: SimpleStrTransformSpace = Field(
        default_factory=SimpleStrTransformSpace
    )
    input_space: StringSpace = Field(  # type: ignore[assignment]
        default_factory=SimpleStringInputSpace,
    )
    input_var: str = "s"

    def eval(self, **kwargs: Any) -> str:
        self.validate_input(**kwargs)
        input = cast(str, kwargs[DEFAULT_STR_INPUT_VAR])
        match self.transform:
            case "lowercase":
                return input.lower()
            case "uppercase":
                return input.upper()
            case "capitalize":
                return input.capitalize()
            case "swapcase":
                return input.swapcase()
            case "reverse":
                return input[::-1]
            case "casefold":
                return input.casefold()
            case "title":
                return input.title()
            case "strip":
                return input.strip()
            case "lstrip":
                return input.lstrip()
            case "rstrip":
                return input.rstrip()
            case "expandtabs":
                return input.expandtabs()
        raise AssertionError("unreachable transform, is validation broken?")

    def render_python(self) -> str:
        v = self.input_var
        match self.transform:
            case "lowercase":
                return f"{v}.lower()"
            case "uppercase":
                return f"{v}.upper()"
            case "capitalize":
                return f"{v}.capitalize()"
            case "swapcase":
                return f"{v}.swapcase()"
            case "reverse":
                return f"{v}[::-1]"
            case "casefold":
                return f"{v}.casefold()"
            case "title":
                return f"{v}.title()"
            case "strip":
                return f"{v}.strip()"
            case "lstrip":
                return f"{v}.lstrip()"
            case "rstrip":
                return f"{v}.rstrip()"
            case "expandtabs":
                return f"{v}.expandtabs()"
        raise AssertionError("unreachable transform")
