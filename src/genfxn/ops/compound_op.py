from __future__ import annotations

from typing import Any

from pydantic import Field

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.categorical_space import CategoricalSpace


class CompoundOp(BaseOp):
    """Base class for ops that parameterize over a family of related leaf ops.

    Subclasses select a specific leaf op at construction time via the
    ``transform`` field (an op_type string), whose valid values are
    enumerated by the ``transform_space`` (a CategoricalSpace subclass).

    Eval and render are delegated to the resolved leaf op instance.
    """

    transform: Any
    transform_space: CategoricalSpace
    resolved_op: Any = Field(default=None, exclude=True, repr=False)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        from genfxn.ops.registry import build_op

        resolved = build_op(self.transform)
        object.__setattr__(self, "resolved_op", resolved)

    def eval(self, **kwargs: Any) -> Any:
        self.validate_input(**kwargs)
        return self.resolved_op.eval(**kwargs)

    def render_python(self) -> str:
        return self.resolved_op.render_python()
