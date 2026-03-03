from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

DEFAULT_MIN_STR_LEN = 0
DEFAULT_MAX_STR_LEN = 10_000
DEFAULT_EXPANDTABS_TABSIZE = 8
DEFAULT_STR_INPUT_VAR = "s"


class Lang(StrEnum):
    PYTHON = "python"


class Alphabet(StrEnum):
    ASCII_ALPHABET = "ascii"


RenderFn = Callable[[str], str]
StrRenderFn = Callable[[], str]
