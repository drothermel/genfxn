from genfxn.bitops.models import BitopsSpec
from genfxn.langs.java._helpers import java_long_literal


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
        "        if (op.equals(\"and_mask\")) {",
        "            value = value & (arg & mask);",
        "        } else if (op.equals(\"or_mask\")) {",
        "            value = value | (arg & mask);",
        "        } else if (op.equals(\"xor_mask\")) {",
        "            value = value ^ (arg & mask);",
        "        } else if (op.equals(\"shl\")) {",
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            value = (value << amt) & mask;",
        "        } else if (op.equals(\"shr_logical\")) {",
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            value = (value & mask) >>> amt;",
        "        } else if (op.equals(\"rotl\")) {",
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            if (amt == 0) {",
        "                value = value & mask;",
        "            } else {",
        "                value = ((value << amt) |",
        "                    (value >>> (widthBits - amt))) & mask;",
        "            }",
        "        } else if (op.equals(\"rotr\")) {",
        "            int amt = (int) Math.floorMod(arg, (long) widthBits);",
        "            if (amt == 0) {",
        "                value = value & mask;",
        "            } else {",
        "                value = ((value >>> amt) |",
        "                    (value << (widthBits - amt))) & mask;",
        "            }",
        "        } else if (op.equals(\"not\")) {",
        "            value = (~value) & mask;",
        "        } else if (op.equals(\"popcount\")) {",
        "            value = (long) Long.bitCount(value & mask);",
        "            value = value & mask;",
        "        } else if (op.equals(\"parity\")) {",
        "            value = (long) (Long.bitCount(value & mask) & 1);",
        "        } else {",
        "            throw new IllegalArgumentException(\"Unsupported op\");",
        "        }",
        "",
        "        value = value & mask;",
        "    }",
        "",
        "    return value;",
        "}",
    ]
    return "\n".join(lines)
