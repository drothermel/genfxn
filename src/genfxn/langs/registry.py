"""Maps languages to their render modules."""

import importlib
from types import ModuleType
from typing import Any

from genfxn.langs.types import Language

# Maps Language -> dict of family -> module path.
# Python points to existing modules; Java/Rust to langs/ subpackages.
_FAMILY_MODULES: dict[Language, dict[str, str]] = {
    Language.PYTHON: {
        "piecewise": "genfxn.piecewise.render",
        "stateful": "genfxn.stateful.render",
        "simple_algorithms": "genfxn.simple_algorithms.render",
        "stack_bytecode": "genfxn.stack_bytecode.render",
        "stringrules": "genfxn.stringrules.render",
    },
    Language.JAVA: {
        "piecewise": "genfxn.langs.java.piecewise",
        "stateful": "genfxn.langs.java.stateful",
        "simple_algorithms": "genfxn.langs.java.simple_algorithms",
        "stack_bytecode": "genfxn.langs.java.stack_bytecode",
        "stringrules": "genfxn.langs.java.stringrules",
    },
    Language.RUST: {
        "piecewise": "genfxn.langs.rust.piecewise",
        "stateful": "genfxn.langs.rust.stateful",
        "simple_algorithms": "genfxn.langs.rust.simple_algorithms",
        "stack_bytecode": "genfxn.langs.rust.stack_bytecode",
        "stringrules": "genfxn.langs.rust.stringrules",
    },
}

# Canonical render function name per family.
_RENDER_FUNCTIONS: dict[str, str] = {
    "piecewise": "render_piecewise",
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
