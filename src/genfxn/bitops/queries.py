import random

from genfxn.bitops.eval import eval_bitops
from genfxn.bitops.models import BitopsAxes, BitopsSpec
from genfxn.core.models import Query, QueryTag, dedupe_queries

I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1


def _clamp_i64(x: int) -> int:
    return min(max(x, I64_MIN), I64_MAX)


def generate_bitops_queries(
    spec: BitopsSpec,
    axes: BitopsAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    mask = (1 << spec.width_bits) - 1
    v_lo, v_hi = axes.value_range
    bounded_lo = max(v_lo, I64_MIN)
    bounded_hi = min(v_hi, I64_MAX)
    if bounded_lo > bounded_hi:
        bounded_lo, bounded_hi = I64_MIN, I64_MAX

    queries: list[Query] = []

    def _append_query(x: int, tag: QueryTag) -> None:
        queries.append(
            Query(
                input=x,
                output=eval_bitops(spec, x),
                tag=tag,
            )
        )

    coverage_inputs = [
        0,
        1,
        -1,
        _clamp_i64(mask),
        _clamp_i64(mask + 1),
    ]
    for x in coverage_inputs:
        _append_query(x, QueryTag.COVERAGE)

    boundary_inputs = [
        bounded_lo,
        bounded_hi,
        _clamp_i64(-mask),
        _clamp_i64(-(mask + 1)),
    ]
    for x in boundary_inputs:
        _append_query(x, QueryTag.BOUNDARY)

    for _ in range(4):
        _append_query(rng.randint(bounded_lo, bounded_hi), QueryTag.TYPICAL)

    adversarial_inputs = [
        0xAAAAAAAA,
        0x55555555,
        -(1 << max(spec.width_bits - 1, 0)),
        (1 << min(spec.width_bits + 4, 63)) - 1,
    ]
    for x in adversarial_inputs:
        _append_query(x, QueryTag.ADVERSARIAL)

    return dedupe_queries(queries)
