from __future__ import annotations

from importlib import import_module
from typing import Any

from pydantic import TypeAdapter

_SPEC_MODELS: dict[str, tuple[str, str]] = {
    "bitops": ("genfxn.bitops.models", "BitopsSpec"),
    "fsm": ("genfxn.fsm.models", "FsmSpec"),
    "graph_queries": ("genfxn.graph_queries.models", "GraphQueriesSpec"),
    "intervals": ("genfxn.intervals.models", "IntervalsSpec"),
    "piecewise": ("genfxn.piecewise.models", "PiecewiseSpec"),
    "sequence_dp": ("genfxn.sequence_dp.models", "SequenceDpSpec"),
    "simple_algorithms": (
        "genfxn.simple_algorithms.models",
        "SimpleAlgorithmsSpec",
    ),
    "stack_bytecode": ("genfxn.stack_bytecode.models", "StackBytecodeSpec"),
    "stateful": ("genfxn.stateful.models", "StatefulSpec"),
    "stringrules": ("genfxn.stringrules.models", "StringRulesSpec"),
    "temporal_logic": ("genfxn.temporal_logic.models", "TemporalLogicSpec"),
}
_SPEC_ADAPTERS: dict[str, TypeAdapter[Any]] = {}


def known_families() -> frozenset[str]:
    return frozenset(_SPEC_MODELS)


def get_spec_adapter(family: str) -> TypeAdapter[Any]:
    adapter = _SPEC_ADAPTERS.get(family)
    if adapter is not None:
        return adapter

    spec_model = _SPEC_MODELS.get(family)
    if spec_model is None:
        supported = ", ".join(sorted(_SPEC_MODELS))
        raise ValueError(f"Unknown family '{family}'. Supported: {supported}")

    module_name, model_name = spec_model
    module = import_module(module_name)
    model_type = getattr(module, model_name)
    adapter = TypeAdapter(model_type)
    _SPEC_ADAPTERS[family] = adapter
    return adapter


def validate_spec_for_family(family: str, spec: Any) -> Any:
    adapter = get_spec_adapter(family)
    return adapter.validate_python(spec)
