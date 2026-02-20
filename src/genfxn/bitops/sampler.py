import random

from genfxn.bitops.models import BitInstruction, BitOp, BitopsAxes, BitopsSpec
from genfxn.core.sampling import intersect_ranges, pick_from_preferred
from genfxn.core.trace import TraceStep, trace_step

_TARGET_N_OPS: dict[int, tuple[int, int]] = {
    1: (1, 2),
    2: (2, 3),
    3: (3, 4),
    4: (4, 5),
    5: (5, 7),
}

_TARGET_WIDTHS: dict[int, list[int]] = {
    1: [8],
    2: [8, 16],
    3: [16, 32],
    4: [16, 32],
    5: [32],
}

_TARGET_OP_PREFS: dict[int, list[BitOp]] = {
    1: [BitOp.XOR_MASK, BitOp.AND_MASK, BitOp.NOT],
    2: [BitOp.XOR_MASK, BitOp.AND_MASK, BitOp.OR_MASK, BitOp.SHL],
    3: [BitOp.SHL, BitOp.SHR_LOGICAL, BitOp.ROTL, BitOp.ROTR, BitOp.NOT],
    4: [BitOp.ROTL, BitOp.ROTR, BitOp.POPCOUNT, BitOp.PARITY, BitOp.XOR_MASK],
    5: [
        BitOp.POPCOUNT,
        BitOp.PARITY,
        BitOp.ROTL,
        BitOp.ROTR,
        BitOp.SHR_LOGICAL,
    ],
}


def _pick_targeted_int(
    base_range: tuple[int, int],
    target_range: tuple[int, int],
    rng: random.Random,
) -> int:
    bounded = intersect_ranges(base_range, target_range)
    if bounded is None:
        return rng.randint(*base_range)
    return rng.randint(*bounded)


def _sample_instruction(
    op: BitOp,
    width_bits: int,
    axes: BitopsAxes,
    rng: random.Random,
) -> BitInstruction:
    if op in {BitOp.AND_MASK, BitOp.OR_MASK, BitOp.XOR_MASK}:
        lo, hi = axes.mask_range
        mask = (1 << width_bits) - 1
        return BitInstruction(op=op, arg=rng.randint(lo, hi) & mask)

    if op in {
        BitOp.SHL,
        BitOp.SHR_LOGICAL,
        BitOp.ROTL,
        BitOp.ROTR,
    }:
        lo, hi = axes.shift_range
        return BitInstruction(op=op, arg=rng.randint(lo, hi))

    return BitInstruction(op=op)


def sample_bitops_spec(
    axes: BitopsAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> BitopsSpec:
    if rng is None:
        rng = random.Random()

    target_difficulty = axes.target_difficulty

    if target_difficulty is None:
        width_bits = rng.choice(axes.width_choices)
        n_ops = rng.randint(*axes.n_ops_range)
        op_pool = axes.allowed_ops
    else:
        width_bits = pick_from_preferred(
            axes.width_choices,
            _TARGET_WIDTHS[target_difficulty],
            rng,
        )
        n_ops = _pick_targeted_int(
            axes.n_ops_range,
            _TARGET_N_OPS[target_difficulty],
            rng,
        )
        preferred = _TARGET_OP_PREFS[target_difficulty]
        preferred_available = [op for op in preferred if op in axes.allowed_ops]
        op_pool = preferred_available or axes.allowed_ops

    trace_step(
        trace,
        "sample_width_bits",
        f"Width bits: {width_bits}",
        width_bits,
    )
    trace_step(
        trace,
        "sample_n_ops",
        f"Operation count: {n_ops}",
        n_ops,
    )

    operations = [
        _sample_instruction(rng.choice(op_pool), width_bits, axes, rng)
        for _ in range(n_ops)
    ]

    return BitopsSpec(width_bits=width_bits, operations=operations)
