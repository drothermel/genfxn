from __future__ import annotations

from abc import ABC
from typing import Any

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.categorical_space import CategoricalSpace


class CompoundOp(BaseOp, ABC):
    """Base class for ops that parameterize over a family of related transforms.

    Subclasses select a specific transform at construction time via the
    ``transform`` field, whose valid values are enumerated by the
    ``transform_space`` (a CategoricalSpace subclass). The ``input_var``
    field controls the variable name used in rendered code.
    """

    transform: Any
    transform_space: CategoricalSpace
    input_var: str = "x"
