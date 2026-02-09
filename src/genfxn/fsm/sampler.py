import random

from genfxn.core.predicates import (
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
)
from genfxn.core.trace import TraceStep, trace_step
from genfxn.fsm.models import (
    FsmAxes,
    FsmSpec,
    MachineType,
    OutputMode,
    PredicateType,
    State,
    Transition,
    UndefinedTransitionPolicy,
)

_TARGET_STATES: dict[int, tuple[int, int]] = {
    1: (2, 2),
    2: (2, 3),
    3: (3, 4),
    4: (4, 5),
    5: (5, 6),
}

_TARGET_TRANSITIONS_PER_STATE: dict[int, tuple[int, int]] = {
    1: (0, 1),
    2: (1, 2),
    3: (1, 3),
    4: (2, 3),
    5: (3, 4),
}

_TARGET_PREDICATE_PREFS: dict[int, list[PredicateType]] = {
    1: [PredicateType.EVEN, PredicateType.ODD],
    2: [
        PredicateType.EVEN,
        PredicateType.ODD,
        PredicateType.LT,
        PredicateType.GT,
    ],
    3: [
        PredicateType.LT,
        PredicateType.LE,
        PredicateType.GT,
        PredicateType.GE,
        PredicateType.EVEN,
        PredicateType.ODD,
    ],
    4: [
        PredicateType.MOD_EQ,
        PredicateType.LT,
        PredicateType.LE,
        PredicateType.GT,
        PredicateType.GE,
    ],
    5: [
        PredicateType.MOD_EQ,
        PredicateType.LE,
        PredicateType.GE,
        PredicateType.LT,
        PredicateType.GT,
    ],
}

_TARGET_MACHINE_PREFS: dict[int, list[MachineType]] = {
    1: [MachineType.MOORE],
    2: [MachineType.MOORE],
    3: [MachineType.MOORE, MachineType.MEALY],
    4: [MachineType.MEALY, MachineType.MOORE],
    5: [MachineType.MEALY],
}

_TARGET_OUTPUT_PREFS: dict[int, list[OutputMode]] = {
    1: [OutputMode.FINAL_STATE_ID],
    2: [OutputMode.FINAL_STATE_ID, OutputMode.ACCEPT_BOOL],
    3: [OutputMode.FINAL_STATE_ID, OutputMode.ACCEPT_BOOL],
    4: [OutputMode.TRANSITION_COUNT, OutputMode.ACCEPT_BOOL],
    5: [OutputMode.TRANSITION_COUNT],
}

_TARGET_POLICY_PREFS: dict[int, list[UndefinedTransitionPolicy]] = {
    1: [UndefinedTransitionPolicy.STAY],
    2: [UndefinedTransitionPolicy.STAY, UndefinedTransitionPolicy.SINK],
    3: [UndefinedTransitionPolicy.STAY, UndefinedTransitionPolicy.SINK],
    4: [UndefinedTransitionPolicy.SINK, UndefinedTransitionPolicy.ERROR],
    5: [UndefinedTransitionPolicy.ERROR],
}


def _intersect_ranges(
    a: tuple[int, int],
    b: tuple[int, int],
) -> tuple[int, int] | None:
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if lo > hi:
        return None
    return (lo, hi)


def _pick_from_preferred[T](
    available: list[T],
    preferred: list[T],
    rng: random.Random,
) -> T:
    preferred_available = [item for item in preferred if item in available]
    if preferred_available:
        return rng.choice(preferred_available)
    return rng.choice(available)


def _pick_targeted_int(
    base_range: tuple[int, int],
    target_range: tuple[int, int],
    rng: random.Random,
) -> int:
    bounded = _intersect_ranges(base_range, target_range)
    if bounded is None:
        return rng.randint(*base_range)
    return rng.randint(*bounded)


def _sample_predicate(
    pred_type: PredicateType,
    threshold_range: tuple[int, int],
    divisor_range: tuple[int, int],
    rng: random.Random,
):
    if pred_type == PredicateType.EVEN:
        return PredicateEven()
    if pred_type == PredicateType.ODD:
        return PredicateOdd()
    if pred_type == PredicateType.LT:
        return PredicateLt(value=rng.randint(*threshold_range))
    if pred_type == PredicateType.LE:
        return PredicateLe(value=rng.randint(*threshold_range))
    if pred_type == PredicateType.GT:
        return PredicateGt(value=rng.randint(*threshold_range))
    if pred_type == PredicateType.GE:
        return PredicateGe(value=rng.randint(*threshold_range))

    divisor = rng.randint(*divisor_range)
    remainder = rng.randint(0, divisor - 1)
    return PredicateModEq(divisor=divisor, remainder=remainder)


def _sample_state(
    state_id: int,
    all_state_ids: list[int],
    axes: FsmAxes,
    target_difficulty: int | None,
    rng: random.Random,
) -> State:
    if target_difficulty is None:
        n_transitions = rng.randint(*axes.transitions_per_state_range)
        predicate_pool = axes.predicate_types
    else:
        n_transitions = _pick_targeted_int(
            axes.transitions_per_state_range,
            _TARGET_TRANSITIONS_PER_STATE[target_difficulty],
            rng,
        )
        preferred = _TARGET_PREDICATE_PREFS[target_difficulty]
        preferred_available = [
            pred for pred in preferred if pred in axes.predicate_types
        ]
        predicate_pool = preferred_available or axes.predicate_types

    transitions: list[Transition] = []
    for _ in range(n_transitions):
        pred_type = rng.choice(predicate_pool)
        predicate = _sample_predicate(
            pred_type,
            axes.threshold_range,
            axes.divisor_range,
            rng,
        )
        transitions.append(
            Transition(
                predicate=predicate,
                target_state_id=rng.choice(all_state_ids),
            )
        )

    return State(
        id=state_id,
        transitions=transitions,
        is_accept=rng.choice([False, True]),
    )


def sample_fsm_spec(
    axes: FsmAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> FsmSpec:
    if rng is None:
        rng = random.Random()

    target_difficulty = axes.target_difficulty
    if target_difficulty is None:
        n_states = rng.randint(*axes.n_states_range)
    else:
        n_states = _pick_targeted_int(
            axes.n_states_range,
            _TARGET_STATES[target_difficulty],
            rng,
        )
    state_ids = list(range(n_states))
    trace_step(
        trace,
        "sample_n_states",
        f"Number of states: {n_states}",
        n_states,
    )

    if target_difficulty is None:
        machine_type = rng.choice(axes.machine_types)
        output_mode = rng.choice(axes.output_modes)
        undefined_policy = rng.choice(axes.undefined_transition_policies)
    else:
        machine_type = _pick_from_preferred(
            axes.machine_types,
            _TARGET_MACHINE_PREFS[target_difficulty],
            rng,
        )
        output_mode = _pick_from_preferred(
            axes.output_modes,
            _TARGET_OUTPUT_PREFS[target_difficulty],
            rng,
        )
        undefined_policy = _pick_from_preferred(
            axes.undefined_transition_policies,
            _TARGET_POLICY_PREFS[target_difficulty],
            rng,
        )
    start_state_id = rng.choice(state_ids)

    trace_step(
        trace,
        "sample_machine_type",
        f"Machine type: {machine_type.value}",
        machine_type.value,
    )
    trace_step(
        trace,
        "sample_output_mode",
        f"Output mode: {output_mode.value}",
        output_mode.value,
    )
    trace_step(
        trace,
        "sample_undefined_policy",
        f"Undefined policy: {undefined_policy.value}",
        undefined_policy.value,
    )

    states = [
        _sample_state(sid, state_ids, axes, target_difficulty, rng)
        for sid in state_ids
    ]

    if not any(state.is_accept for state in states):
        picked = rng.choice(states)
        states = [
            state.model_copy(update={"is_accept": True})
            if state.id == picked.id
            else state
            for state in states
        ]

    return FsmSpec(
        machine_type=machine_type,
        output_mode=output_mode,
        undefined_transition_policy=undefined_policy,
        start_state_id=start_state_id,
        states=states,
    )
