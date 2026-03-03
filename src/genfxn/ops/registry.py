from __future__ import annotations

from typing import Any

from genfxn.ops.base_op import BaseOp
from genfxn.ops.string_ops.registry import STRING_OP_REGISTRY

OpClass = type[BaseOp]

OP_REGISTRY: dict[str, OpClass] = {
    **STRING_OP_REGISTRY,
}


def list_op_types() -> tuple[str, ...]:
    return tuple(sorted(OP_REGISTRY.keys()))


def get_op_cls(op_type: str) -> OpClass:
    op_cls = OP_REGISTRY.get(op_type)
    if op_cls is None:
        supported = ", ".join(list_op_types())
        raise ValueError(f"Unknown op_type '{op_type}'. Supported: {supported}")
    return op_cls


def build_op(op_type: str, **kwargs: Any) -> BaseOp:
    op_cls = get_op_cls(op_type)
    return op_cls(**kwargs)
