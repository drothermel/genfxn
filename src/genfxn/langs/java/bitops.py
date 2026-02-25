from genfxn.bitops.models import BitopsSpec
from genfxn.langs.java._helpers import java_long_literal


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
    "and_mask": ["            value = value & (arg & mask);"],
    "or_mask": ["            value = value | (arg & mask);"],
    "xor_mask": ["            value = value ^ (arg & mask);"],
    "shl": [
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            value = (value << amt) & mask;",
    ],
    "shr_logical": [
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            value = (value & mask) >>> amt;",
    ],
    "rotl": [
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            if (amt == 0) {",
        "                value = value & mask;",
        "            } else {",
        "                value = ((value << amt) |",
        "                    (value >>> (widthBits - amt))) & mask;",
        "            }",
    ],
    "rotr": [
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            if (amt == 0) {",
        "                value = value & mask;",
        "            } else {",
        "                value = ((value >>> amt) |",
        "                    (value << (widthBits - amt))) & mask;",
        "            }",
    ],
    "not": ["            value = (~value) & mask;"],
    "popcount": [
        "            value = (long) Long.bitCount(value & mask);",
        "            value = value & mask;",
    ],
    "parity": ["            value = (long) (Long.bitCount(value & mask) & 1);"],
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
        java_long_literal(instruction.arg if instruction.arg is not None else 0)
        for instruction in spec.operations
    )
    used_ops = _used_ops(spec)

    branch_lines: list[str] = []
    for idx, op in enumerate(used_ops):
        if idx == 0:
            branch_lines.append(f'        if (op.equals("{op}")) {{')
        else:
            branch_lines.append(f'        }} else if (op.equals("{op}")) {{')
        branch_lines.extend(_OP_BRANCH_BODIES[op])
    branch_lines.extend(
        [
            "        } else {",
            '            throw new IllegalArgumentException("Unsupported op");',
            "        }",
        ]
    )

    lines = [
        f"public static long {func_name}(long {var}) {{",
        f"    int widthBits = {spec.width_bits};",
        "    long mask = widthBits == 64 ? -1L : (1L << widthBits) - 1L;",
        "    String[] ops = new String[] {" + ops + "};",
        "    long[] args = new long[] {" + args + "};",
        f"    long value = {var} & mask;",
        "",
        "    for (int i = 0; i < ops.length; i++) {",
        "        String op = ops[i];",
        "        long arg = args[i];",
        "",
        *branch_lines,
        "",
        "        value = value & mask;",
        "    }",
        "",
        "    return value;",
        "}",
    ]
    return "\n".join(lines)
