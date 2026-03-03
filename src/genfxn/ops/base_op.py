from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from genfxn.spaces.space import Space
from genfxn.types import Lang, StrRenderFn


class BaseOp(BaseModel, ABC):
    """Shared base model for operation specs."""

    op_type: Any
    input_space: Space
    renderers: dict[Lang, StrRenderFn] = Field(
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
        self.input_space.validate_member(value)

    @abstractmethod
    def eval(self, **kwargs: Any) -> Any:
        """Evaluate this op in Python."""

    @abstractmethod
    def render_python(self) -> str:
        """Render this op as a Python expression."""

    def render(self, language: Lang = Lang.PYTHON) -> str:
        renderer = self.renderers.get(language)
        if renderer is None:
            supported = ", ".join(
                lang.value for lang in self.supported_languages
            )
            raise ValueError(
                "Unsupported language "
                f"'{language.value}'. Supported: {supported}"
            )
        return renderer()
