from __future__ import annotations

import random
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genfxn.spaces.ascii_char_space import AsciiCharSpace
from genfxn.spaces.char_space import CharSpace
from genfxn.spaces.space import Space
from genfxn.spaces.ordinal_int_space import OrdinalIntSpace
from genfxn.types import DEFAULT_STR_INPUT_VAR


class StringSpace(BaseModel):
    """String space composed from length and character spaces."""

    length_space: Space = Field(default_factory=OrdinalIntSpace)
    char_space: CharSpace = Field(default_factory=AsciiCharSpace)

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    @model_validator(mode="after")
    def validate_spaces(self) -> StringSpace:
        if not isinstance(self.length_space, Space):
            raise ValueError(
                "length_space must implement Space(validate_member, sample)"
            )
        return self

    def validate_member(self, **kwargs: Any) -> None:
        expected_key = DEFAULT_STR_INPUT_VAR
        actual_keys = set(kwargs.keys())
        if actual_keys != {expected_key}:
            missing = [] if expected_key in actual_keys else [expected_key]
            extra = sorted(k for k in actual_keys if k != expected_key)
            raise ValueError(
                f"string input key mismatch; missing={missing}, extra={extra}"
            )
        value = kwargs[expected_key]
        if not isinstance(value, str):
            raise ValueError("value must be a string")

        self.length_space.validate_member(value=len(value))

        for ch in value:
            self.char_space.validate_member(value=ch)

    def sample(self, n_samples: int, rng: random.Random) -> list[str]:
        if n_samples < 0:
            raise ValueError("n_samples must be >= 0")

        lengths = cast(list[int], self.length_space.sample(n_samples, rng))
        samples: list[str] = []
        for length in lengths:
            chars = cast(list[str], self.char_space.sample(length, rng))
            samples.append("".join(chars))

        return samples
