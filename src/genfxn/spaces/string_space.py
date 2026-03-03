from __future__ import annotations

import random
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genfxn.spaces.ascii_char_space import AsciiCharSpace
from genfxn.spaces.categorical_space import CategoricalSpace
from genfxn.spaces.space import Space, get_single_kwarg_value
from genfxn.spaces.uniform_int_space import UniformIntSpace


class StringSpace(BaseModel):
    """String space composed from length and character spaces."""

    length_space: Space = Field(default_factory=UniformIntSpace)
    char_space: Space = Field(default_factory=AsciiCharSpace)

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    @model_validator(mode="after")
    def validate_char_space(self) -> StringSpace:
        if not isinstance(self.length_space, Space):
            raise ValueError(
                "length_space must implement Space(validate_member, sample)"
            )
        if not isinstance(self.char_space, Space):
            raise ValueError(
                "char_space must implement Space(validate_member, sample)"
            )
        if not isinstance(self.char_space, CategoricalSpace):
            raise ValueError("char_space must be a CategoricalSpace")

        AsciiCharSpace.validate_space(
            self.char_space,
            field_name="char_space",
        )
        return self

    def validate_member(self, **kwargs: Any) -> None:
        value = get_single_kwarg_value(kwargs)
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
