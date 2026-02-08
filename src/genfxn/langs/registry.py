import importlib
from typing import Any, Callable

from genfxn.langs.types import Language

_FAMILY_MODULES: dict[Language, dict[str, str]] = {
    Language.PYTHON: {
        "piecewise": "genfxn.piecewise.render",
        "stateful": "genfxn.stateful.render",
        "simple_algorithms": "genfxn.simple_algorithms.render",
        "stringrules": "genfxn.stringrules.render",
    },
    Language.JAVA: {
        "piecewise": "genfxn.langs.java.piecewise",
        "stateful": "genfxn.langs.java.stateful",
        "simple_algorithms": "genfxn.langs.java.simple_algorithms",
        "stringrules": "genfxn.langs.java.stringrules",
    },
    Language.RUST: {
        "piecewise": "genfxn.langs.rust.piecewise",
        "stateful": "genfxn.langs.rust.stateful",
        "simple_algorithms": "genfxn.langs.rust.simple_algorithms",
        "stringrules": "genfxn.langs.rust.stringrules",
    },
}

_RENDER_FUNCTIONS: dict[str, str] = {
    "piecewise": "render_piecewise",
    "stateful": "render_stateful",
    "simple_algorithms": "render_simple_algorithms",
    "stringrules": "render_stringrules",
}


def get_render_fn(language: Language, family: str) -> Callable[..., str]:
    """Return the render function for a language/family pair."""
    lang_modules = _FAMILY_MODULES.get(language)
    if lang_modules is None:
        raise ValueError(f"Unsupported language: {language}")
    module_path = lang_modules.get(family)
    if module_path is None:
        raise ValueError(
            f"No render module for language={language}, family={family}"
        )
    fn_name = _RENDER_FUNCTIONS.get(family)
    if fn_name is None:
        raise ValueError(f"Unknown family: {family}")
    mod = importlib.import_module(module_path)
    fn: Any = getattr(mod, fn_name)
    return fn
