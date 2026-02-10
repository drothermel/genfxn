from typing import Any

from genfxn.temporal_logic.models import TemporalLogicSpec


def _long_literal(value: int) -> str:
    if value == -(1 << 63):
        return "Long.MIN_VALUE"
    return f"{value}L"


def _java_atom_expression(kind: str, constant: int) -> str:
    const = _long_literal(constant)
    if kind == "eq":
        return f"xs[i] == {const}"
    if kind == "ne":
        return f"xs[i] != {const}"
    if kind == "lt":
        return f"xs[i] < {const}"
    if kind == "le":
        return f"xs[i] <= {const}"
    if kind == "gt":
        return f"xs[i] > {const}"
    if kind == "ge":
        return f"xs[i] >= {const}"
    raise ValueError(f"Unsupported predicate kind: {kind}")


def _emit_java_node(
    node: dict[str, Any],
    blocks: list[str],
    next_id: list[int],
) -> str:
    op = str(node["op"])
    node_name = f"_node_{next_id[0]}"
    next_id[0] += 1

    if op == "atom":
        kind = str(node["predicate"])
        constant = int(node["constant"])
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            f"    return {_java_atom_expression(kind, constant)};",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "not":
        child_name = _emit_java_node(node["child"], blocks, next_id)
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            f"    return !{child_name}(xs, i);",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op in {"and", "or"}:
        left_name = _emit_java_node(node["left"], blocks, next_id)
        right_name = _emit_java_node(node["right"], blocks, next_id)
        join = "&&" if op == "and" else "||"
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            f"    return {left_name}(xs, i) {join} {right_name}(xs, i);",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "next":
        child_name = _emit_java_node(node["child"], blocks, next_id)
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            "    if (i + 1 >= xs.length) {",
            "        return false;",
            "    }",
            f"    return {child_name}(xs, i + 1);",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "eventually":
        child_name = _emit_java_node(node["child"], blocks, next_id)
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            "    for (int j = i; j < xs.length; j++) {",
            f"        if ({child_name}(xs, j)) {{",
            "            return true;",
            "        }",
            "    }",
            "    return false;",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "always":
        child_name = _emit_java_node(node["child"], blocks, next_id)
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            "    for (int j = i; j < xs.length; j++) {",
            f"        if (!{child_name}(xs, j)) {{",
            "            return false;",
            "        }",
            "    }",
            "    return true;",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "until":
        left_name = _emit_java_node(node["left"], blocks, next_id)
        right_name = _emit_java_node(node["right"], blocks, next_id)
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            "    for (int j = i; j < xs.length; j++) {",
            f"        if (!{right_name}(xs, j)) {{",
            "            continue;",
            "        }",
            "        boolean valid = true;",
            "        for (int k = i; k < j; k++) {",
            f"            if (!{left_name}(xs, k)) {{",
            "                valid = false;",
            "                break;",
            "            }",
            "        }",
            "        if (valid) {",
            "            return true;",
            "        }",
            "    }",
            "    return false;",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "since":
        left_name = _emit_java_node(node["left"], blocks, next_id)
        right_name = _emit_java_node(node["right"], blocks, next_id)
        body = [
            f"private static boolean {node_name}(long[] xs, int i) {{",
            "    for (int j = i; j >= 0; j--) {",
            f"        if (!{right_name}(xs, j)) {{",
            "            continue;",
            "        }",
            "        boolean valid = true;",
            "        for (int k = j + 1; k <= i; k++) {",
            f"            if (!{left_name}(xs, k)) {{",
            "                valid = false;",
            "                break;",
            "            }",
            "        }",
            "        if (valid) {",
            "            return true;",
            "        }",
            "    }",
            "    return false;",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    raise ValueError(f"Unsupported operator: {op}")


def render_temporal_logic(
    spec: TemporalLogicSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    helper_blocks: list[str] = []
    root_name = _emit_java_node(spec.formula, helper_blocks, [0])

    mode = spec.output_mode.value
    lines = [
        *helper_blocks,
        f"public static long {func_name}(long[] {var}) {{",
        f'    String outputMode = "{mode}";',
        "",
        f"    if ({var}.length == 0) {{",
        '        if (outputMode.equals("first_sat_index")) {',
        "            return -1L;",
        "        }",
        "        return 0L;",
        "    }",
        "",
        f"    boolean[] truthValues = new boolean[{var}.length];",
        f"    for (int i = 0; i < {var}.length; i++) {{",
        f"        truthValues[i] = {root_name}({var}, i);",
        "    }",
        "",
        '    if (outputMode.equals("sat_at_start")) {',
        "        return truthValues[0] ? 1L : 0L;",
        "    }",
        '    if (outputMode.equals("sat_count")) {',
        "        long count = 0L;",
        "        for (boolean value : truthValues) {",
        "            if (value) {",
        "                count += 1L;",
        "            }",
        "        }",
        "        return count;",
        "    }",
        "    for (int idx = 0; idx < truthValues.length; idx++) {",
        "        if (truthValues[idx]) {",
        "            return idx;",
        "        }",
        "    }",
        "    return -1L;",
        "}",
    ]
    return "\n\n".join(lines)
