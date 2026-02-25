from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family

Layer2StrategyFactory = Callable[
    [str, Any, dict[str, Any] | None, int], SearchStrategy[Any]
]
Evaluator = Callable[[Any, Any], Any]


class VerificationFamilyAdapter(Protocol):
    family: str

    def validate_spec(self, spec: Any) -> Any: ...

    def evaluate(self, spec_obj: Any, input_value: Any) -> Any: ...

    def layer2_strategy(
        self,
        *,
        task_id: str,
        spec_obj: Any,
        axes: dict[str, Any] | None,
        seed: int,
    ) -> SearchStrategy[Any]: ...


@dataclass(frozen=True)
class DefaultVerificationFamilyAdapter:
    family: str
    evaluator: Evaluator
    layer2_strategy_factory: Layer2StrategyFactory

    def validate_spec(self, spec: Any) -> Any:
        return validate_spec_for_family(self.family, spec)

    def evaluate(self, spec_obj: Any, input_value: Any) -> Any:
        return self.evaluator(spec_obj, input_value)

    def layer2_strategy(
        self,
        *,
        task_id: str,
        spec_obj: Any,
        axes: dict[str, Any] | None,
        seed: int,
    ) -> SearchStrategy[Any]:
        return self.layer2_strategy_factory(task_id, spec_obj, axes, seed)
