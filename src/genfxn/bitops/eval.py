from genfxn.bitops.models import BitOp, BitopsSpec


def _mask_for_width(width_bits: int) -> int:
    return (1 << width_bits) - 1


def _rotate_left(value: int, amount: int, width_bits: int) -> int:
    mask = _mask_for_width(width_bits)
    amt = amount % width_bits
    v = value & mask
    return ((v << amt) | (v >> (width_bits - amt))) & mask


def _rotate_right(value: int, amount: int, width_bits: int) -> int:
    mask = _mask_for_width(width_bits)
    amt = amount % width_bits
    v = value & mask
    return ((v >> amt) | (v << (width_bits - amt))) & mask


def eval_bitops(spec: BitopsSpec, x: int) -> int:
    width_bits = spec.width_bits
    mask = _mask_for_width(width_bits)
    value = x & mask

    for instruction in spec.operations:
        op = instruction.op
        arg = instruction.arg if instruction.arg is not None else 0

        if op == BitOp.AND_MASK:
            value = value & (arg & mask)
        elif op == BitOp.OR_MASK:
            value = value | (arg & mask)
        elif op == BitOp.XOR_MASK:
            value = value ^ (arg & mask)
        elif op == BitOp.SHL:
            value = (value << (arg % width_bits)) & mask
        elif op == BitOp.SHR_LOGICAL:
            value = (value & mask) >> (arg % width_bits)
        elif op == BitOp.ROTL:
            value = _rotate_left(value, arg, width_bits)
        elif op == BitOp.ROTR:
            value = _rotate_right(value, arg, width_bits)
        elif op == BitOp.NOT:
            value = (~value) & mask
        elif op == BitOp.POPCOUNT:
            value = (value & mask).bit_count() & mask
        elif op == BitOp.PARITY:
            value = (value & mask).bit_count() & 1
        else:  # pragma: no cover - defensive fallback
            raise ValueError(f"Unsupported op: {op.value}")

        value &= mask

    return value
