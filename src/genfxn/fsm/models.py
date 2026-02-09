from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from genfxn.core.predicates import (
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
)


class MachineType(str, Enum):
    MOORE = "moore"
    MEALY = "mealy"


class UndefinedTransitionPolicy(str, Enum):
    SINK = "sink"
    STAY = "stay"
    ERROR = "error"


class OutputMode(str, Enum):
    FINAL_STATE_ID = "final_state_id"
    ACCEPT_BOOL = "accept_bool"
    TRANSITION_COUNT = "transition_count"


class PredicateType(str, Enum):
    EVEN = "even"
    ODD = "odd"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    MOD_EQ = "mod_eq"


FsmPredicate = Annotated[
    PredicateEven
    | PredicateOdd
    | PredicateLt
    | PredicateLe
    | PredicateGt
    | PredicateGe
    | PredicateModEq,
    Field(discriminator="kind"),
]


class Transition(BaseModel):
    predicate: FsmPredicate
    target_state_id: int


class State(BaseModel):
    id: int
    transitions: list[Transition] = Field(default_factory=list)
    is_accept: bool = False


class FsmSpec(BaseModel):
    machine_type: MachineType
    output_mode: OutputMode
    undefined_transition_policy: UndefinedTransitionPolicy
    start_state_id: int
    states: list[State] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_spec(self) -> "FsmSpec":
        ids = [s.id for s in self.states]
        if len(set(ids)) != len(ids):
            raise ValueError("state ids must be unique")

        state_id_set = set(ids)
        if self.start_state_id not in state_id_set:
            raise ValueError("start_state_id must reference an existing state")

        for state in self.states:
            for transition in state.transitions:
                if transition.target_state_id not in state_id_set:
                    raise ValueError(
                        "transition target_state_id must reference an existing "
                        "state"
                    )

        return self


class FsmAxes(BaseModel):
    machine_types: list[MachineType] = Field(
        default_factory=lambda: list(MachineType)
    )
    output_modes: list[OutputMode] = Field(
        default_factory=lambda: list(OutputMode)
    )
    undefined_transition_policies: list[UndefinedTransitionPolicy] = Field(
        default_factory=lambda: list(UndefinedTransitionPolicy)
    )
    predicate_types: list[PredicateType] = Field(
        default_factory=lambda: list(PredicateType)
    )
    n_states_range: tuple[int, int] = Field(default=(2, 6))
    transitions_per_state_range: tuple[int, int] = Field(default=(1, 4))
    target_difficulty: int | None = Field(default=None, ge=1, le=5)
    value_range: tuple[int, int] = Field(default=(-20, 20))
    threshold_range: tuple[int, int] = Field(default=(-10, 10))
    divisor_range: tuple[int, int] = Field(default=(2, 10))

    @model_validator(mode="after")
    def validate_axes(self) -> "FsmAxes":
        if not self.machine_types:
            raise ValueError("machine_types must not be empty")
        if not self.output_modes:
            raise ValueError("output_modes must not be empty")
        if not self.undefined_transition_policies:
            raise ValueError("undefined_transition_policies must not be empty")
        if not self.predicate_types:
            raise ValueError("predicate_types must not be empty")

        for name in (
            "n_states_range",
            "transitions_per_state_range",
            "value_range",
            "threshold_range",
            "divisor_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        lo, _ = self.n_states_range
        if lo < 1:
            raise ValueError("n_states_range: low must be >= 1")

        lo, _ = self.transitions_per_state_range
        if lo < 0:
            raise ValueError("transitions_per_state_range: low must be >= 0")

        lo, _ = self.divisor_range
        if lo < 1:
            raise ValueError("divisor_range: low must be >= 1")

        return self
