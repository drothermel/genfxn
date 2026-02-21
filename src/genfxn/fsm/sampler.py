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
    FsmPredicate,
    FsmSpec,
    PredicateType,
    State,
    Transition,
)


def _sample_predicate(
    pred_type: PredicateType,
    threshold_range: tuple[int, int],
    divisor_range: tuple[int, int],
    rng: random.Random,
) -> FsmPredicate:
    match pred_type:
        case PredicateType.EVEN:
            return PredicateEven()
        case PredicateType.ODD:
            return PredicateOdd()
        case PredicateType.LT:
            return PredicateLt(value=rng.randint(*threshold_range))
        case PredicateType.LE:
            return PredicateLe(value=rng.randint(*threshold_range))
        case PredicateType.GT:
            return PredicateGt(value=rng.randint(*threshold_range))
        case PredicateType.GE:
            return PredicateGe(value=rng.randint(*threshold_range))
        case PredicateType.MOD_EQ:
            divisor_lo, divisor_hi = divisor_range
            if divisor_hi < 1:
                raise ValueError(
                    "divisor_range must include values >= 1 for mod_eq"
                )
            divisor = rng.randint(max(1, divisor_lo), divisor_hi)
            remainder = rng.randint(0, divisor - 1)
            return PredicateModEq(divisor=divisor, remainder=remainder)
        case _:
            raise ValueError(f"Unknown predicate type: {pred_type.value}")


def _sample_state(
    state_id: int,
    all_state_ids: list[int],
    axes: FsmAxes,
    rng: random.Random,
) -> State:
    n_transitions = rng.randint(*axes.transitions_per_state_range)
    transitions: list[Transition] = []
    for _ in range(n_transitions):
        pred_type = rng.choice(axes.predicate_types)
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

    n_states = rng.randint(*axes.n_states_range)
    state_ids = list(range(n_states))
    trace_step(
        trace,
        "sample_n_states",
        f"Number of states: {n_states}",
        n_states,
    )

    machine_type = rng.choice(axes.machine_types)
    output_mode = rng.choice(axes.output_modes)
    undefined_policy = rng.choice(axes.undefined_transition_policies)
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

    states = [_sample_state(sid, state_ids, axes, rng) for sid in state_ids]

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
