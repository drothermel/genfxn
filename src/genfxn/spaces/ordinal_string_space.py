from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from genfxn.spaces.ordinal_space import OrdinalSpace


class OrdinalStringSpace(OrdinalSpace):
    """Ordinal space over strings with a meaningful order.

    Values are provided as a pre-ordered tuple. The first element is
    the lowest, the last is the highest. Useful for ordered labels
    like model sizes ("10M", "40M", "1B") or severity levels.
    """

    kind: Literal["ordinal_string"] = "ordinal_string"
    values: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique(self) -> OrdinalStringSpace:
        if len(set(self.values)) != len(self.values):
            raise ValueError("values must be unique")
        return self

    def ordered_values(self) -> tuple[str, ...]:
        return self.values

    def validate_member(self, **kwargs: Any) -> None:
        from genfxn.spaces.space import get_single_kwarg_value

        value = get_single_kwarg_value(kwargs)
        if not isinstance(value, str):
            raise ValueError(f"value must be a string, got {type(value)}")
        if value not in self.values:
            raise ValueError(
                f"value {value!r} is not in this ordinal space"
            )
