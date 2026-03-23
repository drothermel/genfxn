from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator

from genfxn.spaces.categorical_space import CategoricalSpace


class CharSpace(CategoricalSpace):
    """Categorical space restricted to single characters.

    All values must be strings of length 1. Subclasses can further
    restrict the allowed character set (e.g., ASCII only).
    """

    kind: Literal["char"] = "char"

    @model_validator(mode="after")
    def validate_single_chars(self) -> CharSpace:
        for value in self.values:
            if not isinstance(value, str):
                raise ValueError(f"CharSpace values must be strings, got {type(value)}")
            if len(value) != 1:
                raise ValueError(
                    f"CharSpace values must be single characters, got {value!r}"
                )
        return self
