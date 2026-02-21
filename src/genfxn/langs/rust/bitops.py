from genfxn.bitops.models import BitopsSpec
from genfxn.langs.rust._helpers import rust_i64_literal


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
        '        if op == "and_mask" {',
        "            value &= (arg as u64) & mask;",
        '        } else if op == "or_mask" {',
        "            value |= (arg as u64) & mask;",
        '        } else if op == "xor_mask" {',
        "            value ^= (arg as u64) & mask;",
        '        } else if op == "shl" {',
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            value = (value << amt) & mask;",
        '        } else if op == "shr_logical" {',
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            value = (value & mask) >> amt;",
        '        } else if op == "rotl" {',
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            if amt == 0 {",
        "                value &= mask;",
        "            } else {",
        (
            "                value = "
            "((value << amt) | (value >> (width_bits - amt))) & mask;"
        ),
        "            }",
        '        } else if op == "rotr" {',
        "            let amt = arg.rem_euclid(width_bits as i64) as usize;",
        "            if amt == 0 {",
        "                value &= mask;",
        "            } else {",
        (
            "                value = "
            "((value >> amt) | (value << (width_bits - amt))) & mask;"
        ),
        "            }",
        '        } else if op == "not" {',
        "            value = (!value) & mask;",
        '        } else if op == "popcount" {',
        "            value = ((value & mask).count_ones() as u64) & mask;",
        '        } else if op == "parity" {',
        "            value = ((value & mask).count_ones() as u64) & 1;",
        "        } else {",
        '            panic!("Unsupported op");',
        "        }",
        "",
        "        value &= mask;",
        "    }",
        "",
        "    value as i64",
        "}",
    ]
    return "\n".join(lines)
