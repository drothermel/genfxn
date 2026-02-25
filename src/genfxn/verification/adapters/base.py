from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family

Layer2StrategyFactory = Callable[
    [str, Any, dict[str, Any] | None, int], SearchStrategy[Any]
]
Evaluator = Callable[[Any, Any], Any]
Layer3Mode = Literal["train", "heldout"]


@dataclass(frozen=True)
class Layer3MutantCandidate:
    mutant_spec: dict[str, Any]
    mutant_kind: str
    rule_id: str
    metadata: dict[str, Any]


Layer3MutantFactory = Callable[
    [str, Any, dict[str, Any], int, int, Layer3Mode],
    list[Layer3MutantCandidate],
]


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

    def layer3_mutants(
        self,
        *,
        task_id: str,
        spec_obj: Any,
        spec_dict: dict[str, Any],
        budget: int,
        seed: int,
        mode: Layer3Mode,
    ) -> list[Layer3MutantCandidate]: ...


@dataclass(frozen=True)
class DefaultVerificationFamilyAdapter:
    family: str
    evaluator: Evaluator
    layer2_strategy_factory: Layer2StrategyFactory
    layer3_mutant_factory: Layer3MutantFactory

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

    def layer3_mutants(
        self,
        *,
        task_id: str,
        spec_obj: Any,
        spec_dict: dict[str, Any],
        budget: int,
        seed: int,
        mode: Layer3Mode,
    ) -> list[Layer3MutantCandidate]:
        return self.layer3_mutant_factory(
            task_id,
            spec_obj,
            spec_dict,
            budget,
            seed,
            mode,
        )
