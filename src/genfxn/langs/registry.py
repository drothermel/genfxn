"""Maps languages to their render modules."""

import importlib
from types import ModuleType
from typing import Any

from genfxn.langs.types import Language

# Maps Language -> dict of family -> module path.
# Python points to existing modules; Java/Rust to langs/ subpackages.
_FAMILY_MODULES: dict[Language, dict[str, str]] = {
    Language.PYTHON: {
        "bitops": "genfxn.bitops.render",
        "fsm": "genfxn.fsm.render",
        "graph_queries": "genfxn.graph_queries.render",
        "intervals": "genfxn.intervals.render",
        "piecewise": "genfxn.piecewise.render",
        "sequence_dp": "genfxn.sequence_dp.render",
        "stateful": "genfxn.stateful.render",
        "simple_algorithms": "genfxn.simple_algorithms.render",
        "stack_bytecode": "genfxn.stack_bytecode.render",
        "stringrules": "genfxn.stringrules.render",
    },
    Language.JAVA: {
        "bitops": "genfxn.langs.java.bitops",
        "fsm": "genfxn.langs.java.fsm",
        "graph_queries": "genfxn.langs.java.graph_queries",
        "intervals": "genfxn.langs.java.intervals",
        "piecewise": "genfxn.langs.java.piecewise",
        "sequence_dp": "genfxn.langs.java.sequence_dp",
        "stateful": "genfxn.langs.java.stateful",
        "simple_algorithms": "genfxn.langs.java.simple_algorithms",
        "stack_bytecode": "genfxn.langs.java.stack_bytecode",
        "stringrules": "genfxn.langs.java.stringrules",
    },
    Language.RUST: {
        "bitops": "genfxn.langs.rust.bitops",
        "fsm": "genfxn.langs.rust.fsm",
        "graph_queries": "genfxn.langs.rust.graph_queries",
        "intervals": "genfxn.langs.rust.intervals",
        "piecewise": "genfxn.langs.rust.piecewise",
        "sequence_dp": "genfxn.langs.rust.sequence_dp",
        "stateful": "genfxn.langs.rust.stateful",
        "simple_algorithms": "genfxn.langs.rust.simple_algorithms",
        "stack_bytecode": "genfxn.langs.rust.stack_bytecode",
        "stringrules": "genfxn.langs.rust.stringrules",
    },
}

# Canonical render function name per family.
_RENDER_FUNCTIONS: dict[str, str] = {
    "bitops": "render_bitops",
    "fsm": "render_fsm",
    "graph_queries": "render_graph_queries",
    "intervals": "render_intervals",
    "piecewise": "render_piecewise",
    "sequence_dp": "render_sequence_dp",
    "stateful": "render_stateful",
    "simple_algorithms": "render_simple_algorithms",
    "stack_bytecode": "render_stack_bytecode",
    "stringrules": "render_stringrules",
}


def get_render_fn(language: Language, family: str) -> Any:
    """Return the render function for a language/family pair."""
    family_map = _FAMILY_MODULES.get(language)
    if family_map is None:
        raise ValueError(f"Unsupported language: {language}")
    module_path = family_map.get(family)
    if module_path is None:
        raise ValueError(
            f"Unsupported family '{family}' for language {language}"
        )
    fn_name = _RENDER_FUNCTIONS.get(family)
    if fn_name is None:
        raise ValueError(f"Unknown family: {family}")
    module: ModuleType = importlib.import_module(module_path)
    return getattr(module, fn_name)
