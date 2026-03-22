from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.string_space import StringSpace
from genfxn.templates.str_templates import (
    eval_guarded_str_expr,
    render_guarded_str_method,
)
from genfxn.types import DEFAULT_STR_INPUT_VAR


class CapitalizeStrOp(BaseOp):
    """Op spec for capitalizing a string."""

    op_type: Literal["capitalize_str"] = "capitalize_str"
    input_space: StringSpace = Field(  # type: ignore[assignment]
        default_factory=StringSpace,
    )

    def eval(self, **kwargs: Any) -> str:
        self.validate_input(**kwargs)
        input = cast(str, kwargs[DEFAULT_STR_INPUT_VAR])
        return eval_guarded_str_expr(input, str.capitalize)

    def render_python(self) -> str:
        return render_guarded_str_method("capitalize")
