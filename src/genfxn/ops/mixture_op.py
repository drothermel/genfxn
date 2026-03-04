from __future__ import annotations

import random
from typing import Any, Literal

from pydantic import Field, model_validator

from genfxn.ops.base_op import BaseOp
from genfxn.spaces.space import Space
from genfxn.types import DEFAULT_STR_INPUT_VAR


class MixtureOp(BaseOp):
    """Weighted random choice over registered operations."""

    op_type: Literal["mixture"] = "mixture"
    choices: tuple[str, ...]
    weights: list[float] = Field(min_length=1)
    input_space: Space
    rng: random.Random = Field(default_factory=random.Random, exclude=True)

    @model_validator(mode="after")
    def validate_mixture(self) -> MixtureOp:
        if len(self.choices) == 0:
            raise ValueError("choices must be non-empty")

        if len(set(self.choices)) != len(self.choices):
            raise ValueError("choices must be unique")

        if len(self.weights) != len(self.choices):
            raise ValueError("weights length must match choices length")
        if any(weight <= 0 for weight in self.weights):
            raise ValueError("weights must be > 0")

        # Ensure every referenced op_type exists and can share input_space.
        from genfxn.ops.registry import build_op

        for op_type in self.choices:
            build_op(op_type, input_space=self.input_space)

        return self

    def eval(self, **kwargs: Any) -> Any:
        from genfxn.ops.registry import build_op

        self.validate_input(**kwargs)

        idx = self.rng.choices(
            population=range(len(self.choices)),
            weights=self.weights,
            k=1,
        )[0]
        chosen = self.choices[idx]
        op = build_op(chosen, input_space=self.input_space)
        op.validate_input(**kwargs)
        return op.eval(**kwargs)

    def render_python(self) -> str:
        from genfxn.ops.registry import build_op

        choice_exprs: list[str] = []
        for op_type in self.choices:
            op = build_op(op_type, input_space=self.input_space)
            choice_exprs.append(op.render_python())
        population = list(range(len(self.choices)))
        weights_expr = repr(self.weights)
        lines = [
            f"def mixture_generated({DEFAULT_STR_INPUT_VAR}):",
            "    import random as _random",
            (
                "    _idx = _random.choices("
                f"population={population!r}, "
                f"weights={weights_expr}, k=1"
                ")[0]"
            ),
        ]
        for idx, (op_type, expr) in enumerate(
            zip(self.choices, choice_exprs, strict=True)
        ):
            lines.append(f"    if _idx == {idx}:  # {op_type}")
            lines.append(f"        return {expr}")
        lines.append('    raise AssertionError("unreachable mixture index")')
        return "\n".join(lines)
