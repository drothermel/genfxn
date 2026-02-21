from genfxn.fsm.models import FsmSpec, OutputMode, UndefinedTransitionPolicy
from genfxn.langs.rust.predicates import render_predicate_rust


def _render_state_transitions(spec: FsmSpec, counter_var: str) -> list[str]:
    lines: list[str] = []
    states = sorted(spec.states, key=lambda s: s.id)
    for idx, state in enumerate(states):
        prefix = "if" if idx == 0 else "else if"
        lines.append(f"        {prefix} state == {state.id} {{")
        if not state.transitions:
            lines.append("            // no transitions")
        for transition in state.transitions:
            pred = render_predicate_rust(transition.predicate, "x")
            lines.append(f"            if !matched && ({pred}) {{")
            lines.append(
                f"                state = {transition.target_state_id};"
            )
            lines.append(f"                {counter_var} += 1;")
            lines.append("                matched = true;")
            lines.append("            }")
        lines.append("        }")
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
    counter_var = (
        "transition_count"
        if spec.output_mode == OutputMode.TRANSITION_COUNT
        else "_transition_count"
    )
    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        f"    let mut state: i64 = {spec.start_state_id};",
        f"    let mut {counter_var}: i64 = 0;",
        "",
        f"    for &x in {var} {{",
        "        let mut matched = false;",
    ]
    lines.extend(_render_state_transitions(spec, counter_var))
    lines.extend(
        [
            "",
            "        if matched {",
            "            continue;",
            "        }",
        ]
    )

    if spec.undefined_transition_policy == UndefinedTransitionPolicy.STAY:
        lines.append("        continue;")
    elif spec.undefined_transition_policy == UndefinedTransitionPolicy.SINK:
        lines.extend(
            [
                f"        let sink_state_id: i64 = {sink_state_id};",
                "        state = sink_state_id;",
                f"        {counter_var} += 1;",
                "        continue;",
            ]
        )
    else:
        lines.append(
            '        panic!("undefined transition encountered under error '
            'policy");'
        )

    lines.append("    }")
    lines.append("")
    if spec.output_mode == OutputMode.FINAL_STATE_ID:
        lines.append("    state")
    elif spec.output_mode == OutputMode.TRANSITION_COUNT:
        lines.append(f"    {counter_var}")
    else:
        lines.extend(
            [
                f"    if {_render_accept_expr(spec)} {{",
                "        1",
                "    } else {",
                "        0",
                "    }",
            ]
        )
    lines.append("}")
    return "\n".join(lines)
