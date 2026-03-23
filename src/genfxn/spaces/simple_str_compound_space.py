from __future__ import annotations

from pydantic import Field, model_validator

from genfxn.ops.string_ops.registry import STRING_OP_REGISTRY
from genfxn.spaces.categorical_space import CategoricalSpace


def _default_values() -> tuple[str, ...]:
    return tuple(STRING_OP_REGISTRY.keys())


class SimpleStrCompoundSpace(CategoricalSpace):
    """Categorical space over leaf string op_type values.

    Defaults to all op_types in STRING_OP_REGISTRY. Validates that
    every value is a registered string op_type.
    """

    values: tuple[str, ...] = Field(  # type: ignore[assignment]
        default_factory=_default_values,
    )

    @model_validator(mode="after")
    def validate_values_in_registry(self) -> SimpleStrCompoundSpace:
        invalid = set(self.values) - set(STRING_OP_REGISTRY.keys())
        if invalid:
            raise ValueError(
                f"Unknown string op_type(s): {invalid}. "
                f"Valid: {set(STRING_OP_REGISTRY.keys())}"
            )
        return self
