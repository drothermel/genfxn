from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from genfxn.spaces.categorical_space import CategoricalSpace


class AsciiCharSpace(CategoricalSpace):
    """Categorical space over ASCII characters."""

    kind: Literal["ascii_char"] = "ascii_char"
    values: tuple[str, ...] = Field(
        default_factory=lambda: tuple(chr(i) for i in range(128))
    )

    @model_validator(mode="after")
    def validate_default_values(self) -> AsciiCharSpace:
        self.validate_space(self)
        return self

    @classmethod
    def validate_space(
        cls,
        space: CategoricalSpace,
        *,
        field_name: str = "space",
        allow_multi_char: bool = False,
        require_alpha: bool = False,
    ) -> None:
        for value in space.values:
            if not isinstance(value, str):
                raise ValueError(f"{field_name} values must be strings")

            if not allow_multi_char and len(value) != 1:
                raise ValueError(
                    f"{field_name} values must be single characters"
                )

            if any(ord(ch) >= 128 for ch in value):
                raise ValueError(f"{field_name} values must be ASCII")

            if require_alpha and not value.isalpha():
                raise ValueError(
                    f"{field_name} values must contain only letters"
                )
