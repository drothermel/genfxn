from typing import Any

from genfxn.langs.rust._helpers import rust_i64_literal
from genfxn.temporal_logic.models import TemporalLogicSpec


def _i64_literal(value: int) -> str:
    """Backward-compatible alias for legacy tests/callers."""
    return rust_i64_literal(value)


def _rust_atom_expression(kind: str, constant: int) -> str:
    const = rust_i64_literal(constant)
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


def _emit_rust_node(
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
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            f"    {_rust_atom_expression(kind, constant)}",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "not":
        child_name = _emit_rust_node(node["child"], blocks, next_id)
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            f"    !{child_name}(xs, i)",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op in {"and", "or"}:
        left_name = _emit_rust_node(node["left"], blocks, next_id)
        right_name = _emit_rust_node(node["right"], blocks, next_id)
        join = "&&" if op == "and" else "||"
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            f"    {left_name}(xs, i) {join} {right_name}(xs, i)",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "next":
        child_name = _emit_rust_node(node["child"], blocks, next_id)
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            "    if i + 1 >= xs.len() {",
            "        return false;",
            "    }",
            f"    {child_name}(xs, i + 1)",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "eventually":
        child_name = _emit_rust_node(node["child"], blocks, next_id)
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            "    for j in i..xs.len() {",
            f"        if {child_name}(xs, j) {{",
            "            return true;",
            "        }",
            "    }",
            "    false",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "always":
        child_name = _emit_rust_node(node["child"], blocks, next_id)
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            "    for j in i..xs.len() {",
            f"        if !{child_name}(xs, j) {{",
            "            return false;",
            "        }",
            "    }",
            "    true",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "until":
        left_name = _emit_rust_node(node["left"], blocks, next_id)
        right_name = _emit_rust_node(node["right"], blocks, next_id)
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            "    for j in i..xs.len() {",
            f"        if !{right_name}(xs, j) {{",
            "            continue;",
            "        }",
            "        let mut valid = true;",
            "        for k in i..j {",
            f"            if !{left_name}(xs, k) {{",
            "                valid = false;",
            "                break;",
            "            }",
            "        }",
            "        if valid {",
            "            return true;",
            "        }",
            "    }",
            "    false",
            "}",
        ]
        blocks.append("\n".join(body))
        return node_name

    if op == "since":
        left_name = _emit_rust_node(node["left"], blocks, next_id)
        right_name = _emit_rust_node(node["right"], blocks, next_id)
        body = [
            f"fn {node_name}(xs: &[i64], i: usize) -> bool {{",
            "    for j in (0..=i).rev() {",
            f"        if !{right_name}(xs, j) {{",
            "            continue;",
            "        }",
            "        let mut valid = true;",
            "        for k in (j + 1)..=i {",
            f"            if !{left_name}(xs, k) {{",
            "                valid = false;",
            "                break;",
            "            }",
            "        }",
            "        if valid {",
            "            return true;",
            "        }",
            "    }",
            "    false",
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
    root_name = _emit_rust_node(spec.formula, helper_blocks, [0])

    mode = spec.output_mode.value
    indented_blocks: list[str] = []
    for block in helper_blocks:
        indented_block = "\n".join(f"    {line}" for line in block.splitlines())
        indented_blocks.append(indented_block)
    helpers_section = "\n\n".join(indented_blocks) if indented_blocks else ""

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
    ]
    if helpers_section:
        lines.extend(["", helpers_section])
    lines += [
        "",
        f'    let output_mode = "{mode}";',
        "",
        f"    if {var}.is_empty() {{",
        '        if output_mode == "first_sat_index" {',
        "            return -1;",
        "        }",
        "        return 0;",
        "    }",
        "",
        (
            f"    let truth_values: Vec<bool> = (0..{var}.len())"
            f".map(|i| {root_name}({var}, i)).collect();"
        ),
        '    if output_mode == "sat_at_start" {',
        "        return if truth_values[0] { 1 } else { 0 };",
        "    }",
        '    if output_mode == "sat_count" {',
        (
            "        return truth_values.iter()"
            ".filter(|value| **value).count() as i64;"
        ),
        "    }",
        "    for (idx, value) in truth_values.iter().enumerate() {",
        "        if *value {",
        "            return idx as i64;",
        "        }",
        "    }",
        "    -1",
        "}",
    ]
    return "\n".join(lines)
