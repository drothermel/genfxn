from __future__ import annotations

from typing import Any

from genfxn.ops.base_op import BaseOp
from genfxn.ops.string_ops.capitalize_str_op import CapitalizeStrOp
from genfxn.ops.string_ops.casefold_str_op import CasefoldStrOp
from genfxn.ops.string_ops.expandtabs_str_op import ExpandtabsStrOp
from genfxn.ops.string_ops.lower_str_op import LowerStrOp
from genfxn.ops.string_ops.lstrip_str_op import LstripStrOp
from genfxn.ops.string_ops.reverse_str_op import ReverseStrOp
from genfxn.ops.string_ops.rstrip_str_op import RstripStrOp
from genfxn.ops.string_ops.strip_str_op import StripStrOp
from genfxn.ops.string_ops.swapcase_str_op import SwapcaseStrOp
from genfxn.ops.string_ops.title_str_op import TitleStrOp
from genfxn.ops.string_ops.upper_str_op import UpperStrOp

StringOpClass = type[BaseOp]

STRING_OP_REGISTRY: dict[str, StringOpClass] = {
    "lower_str": LowerStrOp,
    "upper_str": UpperStrOp,
    "capitalize_str": CapitalizeStrOp,
    "swapcase_str": SwapcaseStrOp,
    "reverse_str": ReverseStrOp,
    "casefold_str": CasefoldStrOp,
    "title_str": TitleStrOp,
    "strip_str": StripStrOp,
    "lstrip_str": LstripStrOp,
    "rstrip_str": RstripStrOp,
    "expandtabs_str": ExpandtabsStrOp,
}


def list_string_op_types() -> tuple[str, ...]:
    return tuple(sorted(STRING_OP_REGISTRY.keys()))


def get_string_op_cls(op_type: str) -> StringOpClass:
    op_cls = STRING_OP_REGISTRY.get(op_type)
    if op_cls is None:
        supported = ", ".join(list_string_op_types())
        raise ValueError(
            f"Unknown string op_type '{op_type}'. Supported: {supported}"
        )
    return op_cls


def build_string_op(op_type: str, **kwargs: Any) -> BaseOp:
    op_cls = get_string_op_cls(op_type)
    return op_cls(**kwargs)
