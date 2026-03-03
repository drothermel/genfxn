from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.string_space import StringSpace
from genfxn.templates.str_templates import (
    eval_guarded_str_expr,
    render_guarded_str_method,
)


class RstripStrOp(BaseOp):
    """Op spec for right-stripping a string."""

    op_type: Literal["rstrip_str"] = "rstrip_str"
    input_space: StringSpace = Field(default_factory=StringSpace)

    def eval(self, **kwargs: Any) -> str:
        if "input" not in kwargs or len(kwargs) != 1:
            raise ValueError(
                "eval requires exactly one keyword argument: input"
            )
        input = kwargs["input"]
        self.validate_input(input)
        return eval_guarded_str_expr(cast(str, input), str.rstrip)

    def render_python(self) -> str:
        return render_guarded_str_method("rstrip")
