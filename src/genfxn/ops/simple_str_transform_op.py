from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from genfxn.spaces.simple_str_transform_space import (
    SimpleStrTransformSpace,
    SimpleStrTransformType,
)
from genfxn.spaces.simple_string_input_space import SimpleStringInputSpace
from genfxn.spaces.string_space import StringSpace
from genfxn.types import DEFAULT_STR_INPUT_VAR, Lang, RenderFn


class SimpleStrTransformOp(BaseModel):
    """Op spec for simple parameter-free string transforms."""

    op_type: Literal["simple_str_transform"] = "simple_str_transform"
    transform: SimpleStrTransformType
    transform_space: SimpleStrTransformSpace = Field(
        default_factory=SimpleStrTransformSpace
    )
    input_space: StringSpace = Field(default_factory=SimpleStringInputSpace)
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
        self.input_space.validate_member(**{DEFAULT_STR_INPUT_VAR: value})

    # Handle len=0 case directly.  One source of truth -> render
    def eval(self, input: str) -> str:
        self.validate_input(input)
        match self.transform:
            case "lowercase":
                return input.lower()
            case "uppercase":
                return input.upper()
            case "capitalize":
                return input.capitalize()
            case "swapcase":
                return input.swapcase()
            case "reverse":
                return input[::-1]
            case "casefold":
                return input.casefold()
            case "title":
                return input.title()
            case "strip":
                return input.strip()
            case "lstrip":
                return input.lstrip()
            case "rstrip":
                return input.rstrip()
            case "expandtabs":
                return input.expandtabs()
        raise AssertionError("unreachable transform, is validation broken?")

    def render_python(self, input_var: str = "s") -> str:
        match self.transform:
            case "lowercase":
                return f"{input_var}.lower()"
            case "uppercase":
                return f"{input_var}.upper()"
            case "capitalize":
                return f"{input_var}.capitalize()"
            case "swapcase":
                return f"{input_var}.swapcase()"
            case "reverse":
                return f"{input_var}[::-1]"
            case "casefold":
                return f"{input_var}.casefold()"
            case "title":
                return f"{input_var}.title()"
            case "strip":
                return f"{input_var}.strip()"
            case "lstrip":
                return f"{input_var}.lstrip()"
            case "rstrip":
                return f"{input_var}.rstrip()"
            case "expandtabs":
                return f"{input_var}.expandtabs()"
        raise AssertionError("unreachable transform")

    def render(self, language: Lang = Lang.PYTHON, input_var: str = "s") -> str:
        renderer = self.renderers.get(language)
        if renderer is None:
            supported = ", ".join(
                lang.value for lang in self.supported_languages
            )
            raise ValueError(
                "Unsupported language "
                f"'{language.value}'. Supported: {supported}"
            )
        typed_renderer = renderer
        return typed_renderer(input_var)
