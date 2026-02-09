from genfxn.bitops.models import BitopsSpec


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
            "        if op == 'and_mask':",
            "            value = value & (arg & mask)",
            "        elif op == 'or_mask':",
            "            value = value | (arg & mask)",
            "        elif op == 'xor_mask':",
            "            value = value ^ (arg & mask)",
            "        elif op == 'shl':",
            "            value = (value << (arg % width_bits)) & mask",
            "        elif op == 'shr_logical':",
            "            value = (value & mask) >> (arg % width_bits)",
            "        elif op == 'rotl':",
            "            amt = arg % width_bits",
            "            value = (",
            "                (value << amt) | (value >> (width_bits - amt))",
            "            ) & mask",
            "        elif op == 'rotr':",
            "            amt = arg % width_bits",
            "            value = (",
            "                (value >> amt) | (value << (width_bits - amt))",
            "            ) & mask",
            "        elif op == 'not':",
            "            value = (~value) & mask",
            "        elif op == 'popcount':",
            "            value = (value & mask).bit_count() & mask",
            "        elif op == 'parity':",
            "            value = (value & mask).bit_count() & 1",
            "        else:",
            "            raise ValueError('Unsupported op')",
            "",
            "        value = value & mask",
            "",
            "    return value",
        ]
    )

    return "\n".join(lines)
