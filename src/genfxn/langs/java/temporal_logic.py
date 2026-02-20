from typing import Any

from genfxn.langs.java._helpers import java_long_literal
from genfxn.temporal_logic.models import TemporalLogicSpec


def _long_literal(value: int) -> str:
    """Backward-compatible alias for legacy tests/callers."""
    return java_long_literal(value)


def _java_atom_expression(kind: str, constant: int, var: str) -> str:
    const = java_long_literal(constant)
    if kind == "eq":
        return f"{var}[i] == {const}"
    if kind == "ne":
        return f"{var}[i] != {const}"
    if kind == "lt":
        return f"{var}[i] < {const}"
    if kind == "le":
        return f"{var}[i] <= {const}"
    if kind == "gt":
        return f"{var}[i] > {const}"
    if kind == "ge":
        return f"{var}[i] >= {const}"
    raise ValueError(f"Unsupported predicate kind: {kind}")


def _emit_java_node(
    node: dict[str, Any],
    blocks: list[str],
    next_id: list[int],
    var: str,
) -> str:
    op = str(node["op"])
    node_name = f"_node_{next_id[0]}"
    next_id[0] += 1

    if op == "atom":
        kind = str(node["predicate"])
        constant = int(node["constant"])
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            return {_java_atom_expression(kind, constant, var)};",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "not":
        child_name = _emit_java_node(node["child"], blocks, next_id, var)
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            return !{child_name}(i);",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op in {"and", "or"}:
        left_name = _emit_java_node(node["left"], blocks, next_id, var)
        right_name = _emit_java_node(node["right"], blocks, next_id, var)
        join = "&&" if op == "and" else "||"
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            return {left_name}(i) {join} {right_name}(i);",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "next":
        child_name = _emit_java_node(node["child"], blocks, next_id, var)
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            if (i + 1 >= {var}.length) {{",
            "                return false;",
            "            }",
            f"            return {child_name}(i + 1);",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "eventually":
        child_name = _emit_java_node(node["child"], blocks, next_id, var)
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            for (int j = i; j < {var}.length; j++) {{",
            f"                if ({child_name}(j)) {{",
            "                    return true;",
            "                }",
            "            }",
            "            return false;",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "always":
        child_name = _emit_java_node(node["child"], blocks, next_id, var)
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            for (int j = i; j < {var}.length; j++) {{",
            f"                if (!{child_name}(j)) {{",
            "                    return false;",
            "                }",
            "            }",
            "            return true;",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "until":
        left_name = _emit_java_node(node["left"], blocks, next_id, var)
        right_name = _emit_java_node(node["right"], blocks, next_id, var)
        body = [
            f"        boolean {node_name}(int i) {{",
            f"            for (int j = i; j < {var}.length; j++) {{",
            f"                if (!{right_name}(j)) {{",
            "                    continue;",
            "                }",
            "                boolean valid = true;",
            "                for (int k = i; k < j; k++) {",
            f"                    if (!{left_name}(k)) {{",
            "                        valid = false;",
            "                        break;",
            "                    }",
            "                }",
            "                if (valid) {",
            "                    return true;",
            "                }",
            "            }",
            "            return false;",
            "        }",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "since":
        left_name = _emit_java_node(node["left"], blocks, next_id, var)
        right_name = _emit_java_node(node["right"], blocks, next_id, var)
        body = [
            f"        boolean {node_name}(int i) {{",
            "            for (int j = i; j >= 0; j--) {",
            f"                if (!{right_name}(j)) {{",
            "                    continue;",
            "                }",
            "                boolean valid = true;",
            "                for (int k = j + 1; k <= i; k++) {",
            f"                    if (!{left_name}(k)) {{",
            "                        valid = false;",
            "                        break;",
            "                    }",
            "                }",
            "                if (valid) {",
            "                    return true;",
            "                }",
            "            }",
            "            return false;",
            "        }",
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
    root_name = _emit_java_node(spec.formula, helper_blocks, [0], var)

    mode = spec.output_mode.value
    lines = [
        f"public static long {func_name}(long[] {var}) {{",
        f'    String outputMode = "{mode}";',
        "",
        "    class Eval {",
        *helper_blocks,
        "    }",
        "    Eval eval = new Eval();",
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
        f"        truthValues[i] = eval.{root_name}(i);",
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
    return "\n".join(lines)
