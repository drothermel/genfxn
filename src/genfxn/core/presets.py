"""Named axes profiles for task generation."""

import random
from dataclasses import dataclass
from typing import Any

from genfxn.bitops.models import BitopsAxes
from genfxn.fsm.models import FsmAxes
from genfxn.graph_queries.models import GraphQueriesAxes
from genfxn.intervals.models import IntervalsAxes
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.sequence_dp.models import SequenceDpAxes
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.stack_bytecode.models import StackBytecodeAxes
from genfxn.stateful.models import StatefulAxes
from genfxn.stringrules.models import StringRulesAxes
from genfxn.temporal_logic.models import TemporalLogicAxes


@dataclass(frozen=True)
class AxesProfile:
    name: str
    description: str
    axes_overrides: dict[str, Any]


_FAMILY_PROFILES: dict[str, list[AxesProfile]] = {
    "piecewise": [AxesProfile("default", "Default piecewise sampling", {})],
    "stateful": [AxesProfile("default", "Default stateful sampling", {})],
    "simple_algorithms": [
        AxesProfile("default", "Default simple_algorithms sampling", {})
    ],
    "stringrules": [AxesProfile("default", "Default stringrules sampling", {})],
    "stack_bytecode": [
        AxesProfile("default", "Default stack_bytecode sampling", {})
    ],
    "fsm": [AxesProfile("default", "Default fsm sampling", {})],
    "bitops": [AxesProfile("default", "Default bitops sampling", {})],
    "sequence_dp": [AxesProfile("default", "Default sequence_dp sampling", {})],
    "intervals": [AxesProfile("default", "Default intervals sampling", {})],
    "graph_queries": [
        AxesProfile("default", "Default graph_queries sampling", {})
    ],
    "temporal_logic": [
        AxesProfile("default", "Default temporal_logic sampling", {})
    ],
}


def get_family_axes_profiles(family: str) -> list[str]:
    """Return supported profile names for a family."""
    profiles = _FAMILY_PROFILES.get(family)
    if profiles is None:
        raise ValueError(f"Unknown family: {family}")
    return [profile.name for profile in profiles]


def get_axes_for_profile(
    family: str,
    profile: str | None = None,
    rng: random.Random | None = None,
) -> (
    PiecewiseAxes
    | StatefulAxes
    | SimpleAlgorithmsAxes
    | StringRulesAxes
    | StackBytecodeAxes
    | FsmAxes
    | BitopsAxes
    | SequenceDpAxes
    | IntervalsAxes
    | GraphQueriesAxes
    | TemporalLogicAxes
):
    """Build axes from a named profile; defaults to a random profile."""
    profiles = _FAMILY_PROFILES.get(family)
    if profiles is None:
        raise ValueError(f"Unknown family: {family}")

    chosen: AxesProfile | None = None
    if profile is not None:
        for candidate in profiles:
            if candidate.name == profile:
                chosen = candidate
                break
        if chosen is None:
            valid_profiles = [candidate.name for candidate in profiles]
            raise ValueError(
                f"Invalid profile '{profile}' for {family}. "
                f"Valid: {valid_profiles}"
            )
    else:
        if rng is None:
            rng = random.Random()
        chosen = rng.choice(profiles)

    return _build_axes(family, chosen.axes_overrides)


def _build_axes(
    family: str, overrides: dict[str, Any]
) -> (
    PiecewiseAxes
    | StatefulAxes
    | SimpleAlgorithmsAxes
    | StringRulesAxes
    | StackBytecodeAxes
    | FsmAxes
    | BitopsAxes
    | SequenceDpAxes
    | IntervalsAxes
    | GraphQueriesAxes
    | TemporalLogicAxes
):
    match family:
        case "piecewise":
            return PiecewiseAxes(**overrides)
        case "stateful":
            return StatefulAxes(**overrides)
        case "simple_algorithms":
            return SimpleAlgorithmsAxes(**overrides)
        case "stringrules":
            return StringRulesAxes(**overrides)
        case "stack_bytecode":
            return StackBytecodeAxes(**overrides)
        case "fsm":
            return FsmAxes(**overrides)
        case "bitops":
            return BitopsAxes(**overrides)
        case "sequence_dp":
            return SequenceDpAxes(**overrides)
        case "intervals":
            return IntervalsAxes(**overrides)
        case "graph_queries":
            return GraphQueriesAxes(**overrides)
        case "temporal_logic":
            return TemporalLogicAxes(**overrides)
        case _:
            raise ValueError(f"Unknown family: {family}")
