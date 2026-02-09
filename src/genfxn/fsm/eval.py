from genfxn.core.predicates import eval_predicate
from genfxn.fsm.models import (
    FsmSpec,
    OutputMode,
    State,
    UndefinedTransitionPolicy,
)


def _first_matching_target(
    states: dict[int, State],
    state_id: int,
    x: int,
) -> int | None:
    state = states.get(state_id)
    if state is None:
        return None
    for transition in state.transitions:
        if eval_predicate(transition.predicate, x):
            return transition.target_state_id
    return None


def _sink_state_id(spec: FsmSpec) -> int:
    return max(state.id for state in spec.states) + 1


def eval_fsm(spec: FsmSpec, xs: list[int]) -> int:
    states = {state.id: state for state in spec.states}
    current_state_id = spec.start_state_id
    sink_state_id = _sink_state_id(spec)
    transition_count = 0

    for x in xs:
        target = _first_matching_target(states, current_state_id, x)
        if target is not None:
            current_state_id = target
            transition_count += 1
            continue

        if spec.undefined_transition_policy == UndefinedTransitionPolicy.STAY:
            continue

        if spec.undefined_transition_policy == UndefinedTransitionPolicy.SINK:
            current_state_id = sink_state_id
            transition_count += 1
            continue

        raise ValueError(
            "undefined transition encountered under error policy"
        )

    if spec.output_mode == OutputMode.FINAL_STATE_ID:
        return current_state_id

    if spec.output_mode == OutputMode.TRANSITION_COUNT:
        return transition_count

    is_accept = states.get(current_state_id)
    return 1 if is_accept is not None and is_accept.is_accept else 0
