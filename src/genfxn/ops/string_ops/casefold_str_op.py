from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.string_space import StringSpace
from genfxn.templates.str_templates import (
    eval_guarded_str_expr,
    render_guarded_str_method,
)


class CasefoldStrOp(BaseOp):
    """Op spec for casefolding a string."""

    op_type: Literal["casefold_str"] = "casefold_str"
    input_space: StringSpace = Field(default_factory=StringSpace)

    def eval(self, **kwargs: Any) -> str:
        self.validate_input(**kwargs)
        input = cast(str, kwargs["input"])
        return eval_guarded_str_expr(input, str.casefold)

    def render_python(self) -> str:
        return render_guarded_str_method("casefold")
