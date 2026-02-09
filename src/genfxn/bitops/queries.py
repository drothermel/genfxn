import random

from genfxn.bitops.eval import eval_bitops
from genfxn.bitops.models import BitopsAxes, BitopsSpec
from genfxn.core.models import Query, QueryTag, dedupe_queries


def generate_bitops_queries(
    spec: BitopsSpec,
    axes: BitopsAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    mask = (1 << spec.width_bits) - 1
    v_lo, v_hi = axes.value_range

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
        mask,
        mask + 1,
    ]
    for x in coverage_inputs:
        _append_query(x, QueryTag.COVERAGE)

    boundary_inputs = [
        v_lo,
        v_hi,
        -mask,
        -(mask + 1),
    ]
    for x in boundary_inputs:
        _append_query(x, QueryTag.BOUNDARY)

    for _ in range(4):
        _append_query(rng.randint(v_lo, v_hi), QueryTag.TYPICAL)

    adversarial_inputs = [
        0xAAAAAAAA,
        0x55555555,
        -(1 << max(spec.width_bits - 1, 0)),
        (1 << min(spec.width_bits + 4, 63)) - 1,
    ]
    for x in adversarial_inputs:
        _append_query(x, QueryTag.ADVERSARIAL)

    return dedupe_queries(queries)
