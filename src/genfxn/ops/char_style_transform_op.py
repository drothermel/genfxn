from __future__ import annotations

import string
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from genfxn.spaces.categorical_space import CategoricalSpace
from genfxn.spaces.char_style_transform_space import (
    CharStyleTransformSpace,
    CharStyleTransformType,
)
from genfxn.types import Lang, RenderFn


def _lower_alpha_input_space() -> CategoricalSpace:
    return CategoricalSpace(values=tuple(string.ascii_lowercase))


class CharStyleTransformOp(BaseModel):
    """Op spec for transforming a lowercase char to lower/upper/tab."""

    op_type: Literal["char_style_transform"] = "char_style_transform"
    transform: CharStyleTransformType
    transform_space: CharStyleTransformSpace = Field(
        default_factory=CharStyleTransformSpace
    )
    input_space: CategoricalSpace = Field(
        default_factory=_lower_alpha_input_space
    )
    renderers: dict[Lang, RenderFn] = Field(
        default_factory=dict,
        exclude=True,
        repr=False,
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(
            self,
            "renderers",
            {
                Lang.PYTHON: self.render_python,
            },
        )

    @computed_field(return_type=tuple[Lang, ...])
    @property
    def supported_languages(self) -> tuple[Lang, ...]:
        return tuple(self.renderers.keys())

    def validate_input(self, value: object) -> None:
        self.input_space.validate_member(value=value)

    def eval(self, input: str) -> str:
        self.validate_input(input)
        match self.transform:
            case "upper":
                return input.upper()
            case "lower":
                return input.lower()
            case "tab":
                return "\t"
        raise AssertionError("unreachable transform")

    def render_python(self, input_var: str = "ch") -> str:
        match self.transform:
            case "upper":
                return f"{input_var}.upper()"
            case "lower":
                return f"{input_var}.lower()"
            case "tab":
                return r"'\t'"
        raise AssertionError("unreachable transform")

    def render(
        self, language: Lang = Lang.PYTHON, input_var: str = "ch"
    ) -> str:
        renderer = self.renderers.get(language)
        if renderer is None:
            supported = ", ".join(
                lang.value for lang in self.supported_languages
            )
            raise ValueError(
                "Unsupported language "
                f"'{language.value}'. Supported: {supported}"
            )
        return renderer(input_var)
