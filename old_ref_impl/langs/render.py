"""Multi-language rendering dispatcher."""

from typing import Any

from genfxn.langs.registry import get_render_fn, is_known_family
from genfxn.langs.types import Language


def _available_languages(family: str = "piecewise") -> list[Language]:
    """Return languages that have a render function for the requested family."""
    if not is_known_family(family):
        raise ValueError(f"Unknown family: {family}")

    available: list[Language] = []
    for lang in Language:
        try:
            get_render_fn(lang, family)
            available.append(lang)
        except ValueError:
            pass
    return available


def render_all_languages(
    family: str,
    spec: Any,
    languages: list[Language] | None = None,
    func_name: str = "f",
) -> dict[str, str]:
    """Render code for a spec across all requested languages.

    Returns a dict mapping language name to rendered code string.
    """
    if languages is None:
        languages = _available_languages(family)

    result: dict[str, str] = {}
    for lang in languages:
        render_fn = get_render_fn(lang, family)
        result[lang.value] = render_fn(spec, func_name=func_name)
    return result
