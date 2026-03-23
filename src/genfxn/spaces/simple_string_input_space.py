from __future__ import annotations

import random
import string
from typing import cast

from pydantic import Field, model_validator

from genfxn.ops.mixture_op import MixtureOp
from genfxn.spaces.ascii_char_space import AsciiCharSpace
from genfxn.spaces.categorical_space import CategoricalSpace
from genfxn.spaces.char_space import CharSpace
from genfxn.spaces.ordinal_int_space import OrdinalIntSpace
from genfxn.spaces.space import Space
from genfxn.spaces.string_space import StringSpace
from genfxn.types import (
    DEFAULT_MAX_STR_LEN,
    DEFAULT_MIN_STR_LEN,
    DEFAULT_STR_INPUT_VAR,
)


def _core_letter_space() -> CharSpace:
    return CharSpace(values=tuple(string.ascii_lowercase))


def _single_char_lower_str_space() -> StringSpace:
    return StringSpace(
        length_space=OrdinalIntSpace(low=1, high=1),
        char_space=_core_letter_space(),
    )


def _core_style_mixture() -> MixtureOp:
    return MixtureOp(
        choices=("lower_str", "upper_str", "tab_str"),
        weights=[1.0, 1.0, 1.0],
        input_space=_single_char_lower_str_space(),
    )


def _pad_space() -> CategoricalSpace:
    return CategoricalSpace(values=(" ", "\t", " \t", ""))


class SimpleStringInputSpace(StringSpace):
    """Focused string sampler for simple string transforms."""

    core_length_space: Space = Field(
        default_factory=lambda: OrdinalIntSpace(
            low=DEFAULT_MIN_STR_LEN,
            high=DEFAULT_MAX_STR_LEN - 4,
        )
    )
    core_letter_space: Space = Field(default_factory=_core_letter_space)
    core_style_mixture: MixtureOp = Field(default_factory=_core_style_mixture)
    pad_space: Space = Field(default_factory=_pad_space)

    @model_validator(mode="after")
    def validate_sampler_spaces(self) -> SimpleStringInputSpace:
        if not isinstance(self.core_length_space, Space):
            raise ValueError(
                "core_length_space must implement "
                "Space(validate_member, sample)"
            )
        if not isinstance(self.core_letter_space, Space):
            raise ValueError(
                "core_letter_space must implement "
                "Space(validate_member, sample)"
            )
        if not isinstance(self.pad_space, Space):
            raise ValueError(
                "pad_space must implement Space(validate_member, sample)"
            )
        if not isinstance(self.core_letter_space, CategoricalSpace):
            raise ValueError("core_letter_space must be a CategoricalSpace")
        if not isinstance(self.pad_space, CategoricalSpace):
            raise ValueError("pad_space must be a CategoricalSpace")

        AsciiCharSpace.validate_space(
            self.core_letter_space,
            field_name="core_letter_space",
            require_alpha=True,
        )

        AsciiCharSpace.validate_space(
            self.pad_space,
            field_name="pad_space",
            allow_multi_char=True,
        )

        for value in self.core_letter_space.values:
            self.core_style_mixture.validate_input(
                **{DEFAULT_STR_INPUT_VAR: value}
            )

        return self

    def sample(self, n_samples: int, rng: random.Random) -> list[str]:
        if n_samples < 0:
            raise ValueError("n_samples must be >= 0")

        lengths = cast(list[int], self.core_length_space.sample(n_samples, rng))
        left_pads = cast(list[str], self.pad_space.sample(n_samples, rng))
        right_pads = cast(list[str], self.pad_space.sample(n_samples, rng))
        core_style_mixture = self.core_style_mixture.model_copy(
            update={"rng": rng}
        )

        samples: list[str] = []
        for i, core_len in enumerate(lengths):
            core_letters = cast(
                list[str], self.core_letter_space.sample(core_len, rng)
            )
            core_chars = [
                cast(
                    str,
                    core_style_mixture.eval(**{DEFAULT_STR_INPUT_VAR: letter}),
                )
                for letter in core_letters
            ]

            sampled = f"{left_pads[i]}{''.join(core_chars)}{right_pads[i]}"
            self.validate_member(**{DEFAULT_STR_INPUT_VAR: sampled})
            samples.append(sampled)

        return samples
