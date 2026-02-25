from genfxn.bitops.models import BitopsSpec
from genfxn.langs.rust._helpers import rust_i64_literal


def _used_ops(spec: BitopsSpec) -> list[str]:
    used_ops: list[str] = []
    seen_ops: set[str] = set()
    for instruction in spec.operations:
        op = instruction.op.value
        if op in seen_ops:
            continue
        seen_ops.add(op)
        used_ops.append(op)
    return used_ops


_OP_BRANCH_BODIES: dict[str, list[str]] = {
    "and_mask": ["            value &= (arg as u64) & mask;"],
    "or_mask": ["            value |= (arg as u64) & mask;"],
    "xor_mask": ["            value ^= (arg as u64) & mask;"],
    "shl": [
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            value = (value << amt) & mask;",
    ],
    "shr_logical": [
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            value = (value & mask) >> amt;",
    ],
    "rotl": [
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            if amt == 0 {",
        "                value &= mask;",
        "            } else {",
        (
            "                value = "
            "((value << amt) | (value >> (width_bits - amt))) & mask;"
        ),
        "            }",
    ],
    "rotr": [
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            if amt == 0 {",
        "                value &= mask;",
        "            } else {",
        (
            "                value = "
            "((value >> amt) | (value << (width_bits - amt))) & mask;"
        ),
        "            }",
    ],
    "not": ["            value = (!value) & mask;"],
    "popcount": [
        "            value = ((value & mask).count_ones() as u64) & mask;"
    ],
    "parity": ["            value = ((value & mask).count_ones() as u64) & 1;"],
}


def render_bitops(
    spec: BitopsSpec,
    func_name: str = "f",
    var: str = "x",
) -> str:
    ops = ", ".join(
        f'"{instruction.op.value}"' for instruction in spec.operations
    )
    args = ", ".join(
        rust_i64_literal(instruction.arg if instruction.arg is not None else 0)
        for instruction in spec.operations
    )
    n_ops = len(spec.operations)
    used_ops = _used_ops(spec)

    branch_lines: list[str] = []
    for idx, op in enumerate(used_ops):
        if idx == 0:
            branch_lines.append(f'        if op == "{op}" {{')
        else:
            branch_lines.append(f'        }} else if op == "{op}" {{')
        branch_lines.extend(_OP_BRANCH_BODIES[op])
    branch_lines.extend(
        [
            "        } else {",
            '            panic!("Unsupported op");',
            "        }",
        ]
    )

    lines = [
        f"fn {func_name}({var}: i64) -> i64 {{",
        f"    let width_bits: usize = {spec.width_bits};",
        "    let mask: u64 = (1u64 << width_bits) - 1;",
        "    let ops: [&str; " + str(n_ops) + "] = [" + ops + "];",
        "    let args: [i64; " + str(n_ops) + "] = [" + args + "];",
        f"    let mut value: u64 = ({var} as u64) & mask;",
        "",
        "    for i in 0..ops.len() {",
        "        let op = ops[i];",
        "        let arg = args[i];",
        "",
        *branch_lines,
        "",
        "        value &= mask;",
        "    }",
        "",
        "    value as i64",
        "}",
    ]
    return "\n".join(lines)
