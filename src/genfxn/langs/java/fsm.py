from genfxn.fsm.models import FsmSpec, OutputMode, UndefinedTransitionPolicy
from genfxn.langs.java.predicates import render_predicate_java


def _render_state_transitions(spec: FsmSpec) -> list[str]:
    lines: list[str] = []
    states = sorted(spec.states, key=lambda s: s.id)
    for idx, state in enumerate(states):
        prefix = "if" if idx == 0 else "else if"
        lines.append(f"            {prefix} (state == {state.id}) {{")
        if not state.transitions:
            lines.append("                // no transitions")
        for t_idx, transition in enumerate(state.transitions):
            pred = render_predicate_java(
                transition.predicate, "x", int32_wrap=False
            )
            if_kw = "if" if t_idx == 0 else "else if"
            lines.append(f"                {if_kw} ({pred}) {{")
            lines.append(
                "                    state = "
                f"{transition.target_state_id};"
            )
            lines.append("                    transitionCount += 1;")
            lines.append("                    matched = true;")
            lines.append("                }")
        lines.append("            }")
    return lines


def _render_accept_expr(spec: FsmSpec) -> str:
    accept_ids = sorted(state.id for state in spec.states if state.is_accept)
    if not accept_ids:
        return "false"
    if len(accept_ids) == 1:
        return f"state == {accept_ids[0]}"
    return " || ".join(f"state == {state_id}" for state_id in accept_ids)


def render_fsm(spec: FsmSpec, func_name: str = "f", var: str = "xs") -> str:
    sink_state_id = max(state.id for state in spec.states) + 1
    lines = [
        f"public static int {func_name}(int[] {var}) {{",
        f"    int state = {spec.start_state_id};",
        "    int transitionCount = 0;",
        f"    int sinkStateId = {sink_state_id};",
        "",
        f"    for (int x : {var}) {{",
        "        boolean matched = false;",
    ]
    lines.extend(_render_state_transitions(spec))
    lines.extend(
        [
            "",
            "        if (matched) {",
            "            continue;",
            "        }",
        ]
    )

    if spec.undefined_transition_policy == UndefinedTransitionPolicy.STAY:
        lines.append("        continue;")
    elif spec.undefined_transition_policy == UndefinedTransitionPolicy.SINK:
        lines.extend(
            [
                "        state = sinkStateId;",
                "        transitionCount += 1;",
                "        continue;",
            ]
        )
    else:
        lines.append(
            '        throw new IllegalArgumentException("undefined '
            'transition encountered under error policy");'
        )

    lines.append("    }")
    lines.append("")
    if spec.output_mode == OutputMode.FINAL_STATE_ID:
        lines.append("    return state;")
    elif spec.output_mode == OutputMode.TRANSITION_COUNT:
        lines.append("    return transitionCount;")
    else:
        lines.append(f"    return ({_render_accept_expr(spec)}) ? 1 : 0;")
    lines.append("}")
    return "\n".join(lines)
