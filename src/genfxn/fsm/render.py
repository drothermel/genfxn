from genfxn.core.predicates import render_predicate
from genfxn.fsm.models import FsmSpec, OutputMode, UndefinedTransitionPolicy


def render_fsm(spec: FsmSpec, func_name: str = "f", var: str = "xs") -> str:
    # NOTE: `machine_type` is intentionally non-semantic today.
    # We retain it for schema/backward compatibility, but generated runtime
    # behavior is identical for MOORE and MEALY values.
    states_by_id = sorted(spec.states, key=lambda state: state.id)
    sink_state_id = max(state.id for state in states_by_id) + 1

    lines = [f"def {func_name}({var}: list[int]) -> int:"]
    lines.append(f"    state = {spec.start_state_id}")
    lines.append("    transition_count = 0")
    lines.append("    transitions = {")
    for state in states_by_id:
        lines.append(f"        {state.id}: [")
        for transition in state.transitions:
            predicate = render_predicate(transition.predicate, "x")
            lines.append(
                "            (lambda x: "
                f"{predicate}, {transition.target_state_id}),"
            )
        lines.append("        ],")
    lines.append("    }")

    lines.append(f"    sink_state_id = {sink_state_id}")
    lines.append("    accept_states = {")
    for state in states_by_id:
        if state.is_accept:
            lines.append(f"        {state.id},")
    lines.append("    }")

    lines.append(f"    for x in {var}:")
    lines.append("        matched = False")
    lines.append("        for predicate, target in transitions.get(state, []):")
    lines.append("            if predicate(x):")
    lines.append("                state = target")
    lines.append("                transition_count += 1")
    lines.append("                matched = True")
    lines.append("                break")
    lines.append("        if matched:")
    lines.append("            continue")

    if spec.undefined_transition_policy == UndefinedTransitionPolicy.STAY:
        lines.append("        continue")
    elif spec.undefined_transition_policy == UndefinedTransitionPolicy.SINK:
        lines.append("        state = sink_state_id")
        lines.append("        transition_count += 1")
        lines.append("        continue")
    else:
        lines.append(
            "        raise ValueError('undefined transition encountered under "
            "error policy')"
        )

    if spec.output_mode == OutputMode.FINAL_STATE_ID:
        lines.append("    return state")
    elif spec.output_mode == OutputMode.TRANSITION_COUNT:
        lines.append("    return transition_count")
    else:
        lines.append("    return 1 if state in accept_states else 0")

    return "\n".join(lines)
