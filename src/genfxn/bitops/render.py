from genfxn.bitops.models import BitopsSpec


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
    "and_mask": ["            value = value & (arg & mask)"],
    "or_mask": ["            value = value | (arg & mask)"],
    "xor_mask": ["            value = value ^ (arg & mask)"],
    "shl": ["            value = (value << (arg % width_bits)) & mask"],
    "shr_logical": ["            value = (value & mask) >> (arg % width_bits)"],
    "rotl": [
        "            amt = arg % width_bits",
        "            if amt == 0:",
        "                value = value & mask",
        "            else:",
        "                value = (",
        "                    (value << amt)",
        "                    | (value >> (width_bits - amt))",
        "                ) & mask",
    ],
    "rotr": [
        "            amt = arg % width_bits",
        "            if amt == 0:",
        "                value = value & mask",
        "            else:",
        "                value = (",
        "                    (value >> amt)",
        "                    | (value << (width_bits - amt))",
        "                ) & mask",
    ],
    "not": ["            value = (~value) & mask"],
    "popcount": ["            value = (value & mask).bit_count() & mask"],
    "parity": ["            value = (value & mask).bit_count() & 1"],
}


def render_bitops(
    spec: BitopsSpec,
    func_name: str = "f",
    var: str = "x",
) -> str:
    lines = [
        f"def {func_name}({var}: int) -> int:",
        f"    width_bits = {spec.width_bits}",
        "    mask = (1 << width_bits) - 1",
        "    operations = [",
    ]

    for instruction in spec.operations:
        lines.append(
            "        "
            + repr({"op": instruction.op.value, "arg": instruction.arg})
            + ","
        )

    branch_lines: list[str] = []
    for idx, op in enumerate(_used_ops(spec)):
        keyword = "if" if idx == 0 else "elif"
        branch_lines.append(f"        {keyword} op == {op!r}:")
        branch_lines.extend(_OP_BRANCH_BODIES[op])
    branch_lines.extend(
        [
            "        else:",
            "            raise ValueError('Unsupported op')",
        ]
    )

    lines.extend(
        [
            "    ]",
            f"    value = {var} & mask",
            "",
            "    for instruction in operations:",
            "        op = instruction['op']",
            "        arg = instruction['arg']",
            "        if arg is None:",
            "            arg = 0",
            "",
            *branch_lines,
            "",
            "        value = value & mask",
            "",
            "    return value",
        ]
    )

    return "\n".join(lines)
