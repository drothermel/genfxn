from __future__ import annotations

from pydantic import Field, model_validator

from genfxn.ops.string_ops.registry import STRING_OP_REGISTRY
from genfxn.spaces.categorical_space import CategoricalSpace

_DEFAULT_CHAR_STYLE_OPS: tuple[str, ...] = ("upper_str", "lower_str", "tab_str")


class CharStyleCompoundSpace(CategoricalSpace):
    """Categorical space over char-style leaf op_type values.

    Defaults to upper_str, lower_str, tab_str. Validates that every
    value is a registered string op_type.
    """

    values: tuple[str, ...] = Field(  # type: ignore[assignment]
        default=_DEFAULT_CHAR_STYLE_OPS,
    )

    @model_validator(mode="after")
    def validate_values_in_registry(self) -> CharStyleCompoundSpace:
        invalid = set(self.values) - set(STRING_OP_REGISTRY.keys())
        if invalid:
            raise ValueError(
                f"Unknown string op_type(s): {invalid}. "
                f"Valid: {set(STRING_OP_REGISTRY.keys())}"
            )
        return self
