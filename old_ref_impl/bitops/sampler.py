import random

from genfxn.bitops.models import BitInstruction, BitOp, BitopsAxes, BitopsSpec
from genfxn.core.trace import TraceStep, trace_step


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

    width_bits = rng.choice(axes.width_choices)
    n_ops = rng.randint(*axes.n_ops_range)
    op_pool = axes.allowed_ops

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
