from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.string_space import StringSpace
from genfxn.templates.str_templates import (
    eval_guarded_str_expr,
    render_guarded_str_method_with_args,
)
from genfxn.types import DEFAULT_EXPANDTABS_TABSIZE, DEFAULT_STR_INPUT_VAR


class ExpandtabsStrOp(BaseOp):
    """Op spec for expanding tabs in a string."""

    op_type: Literal["expandtabs_str"] = "expandtabs_str"
    input_space: StringSpace = Field(default_factory=StringSpace)

    def eval(self, **kwargs: Any) -> str:
        self.validate_input(**kwargs)
        input = cast(str, kwargs[DEFAULT_STR_INPUT_VAR])
        return eval_guarded_str_expr(
            input,
            lambda s: s.expandtabs(DEFAULT_EXPANDTABS_TABSIZE),
        )

    def render_python(self) -> str:
        return render_guarded_str_method_with_args(
            method_name="expandtabs",
            args=str(DEFAULT_EXPANDTABS_TABSIZE),
        )
