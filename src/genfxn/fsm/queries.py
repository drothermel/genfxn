import random

from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.fsm.eval import eval_fsm
from genfxn.fsm.models import FsmAxes, FsmSpec


def _rand_list(
    length: int,
    value_range: tuple[int, int],
    rng: random.Random,
) -> list[int]:
    lo, hi = value_range
    return [rng.randint(lo, hi) for _ in range(length)]


def generate_fsm_queries(
    spec: FsmSpec,
    axes: FsmAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    v_lo, v_hi = axes.value_range
    n_states = len(spec.states)

    queries: list[Query] = []

    coverage_inputs = [
        [],
        [v_lo],
        [v_hi],
        [0],
        _rand_list(4, axes.value_range, rng),
    ]
    for xs in coverage_inputs:
        queries.append(
            Query(input=xs, output=eval_fsm(spec, xs), tag=QueryTag.COVERAGE)
        )

    boundary_inputs = [
        [v_lo] * 3,
        [v_hi] * 3,
        [v_lo, v_hi, v_lo, v_hi],
    ]
    for xs in boundary_inputs:
        queries.append(
            Query(input=xs, output=eval_fsm(spec, xs), tag=QueryTag.BOUNDARY)
        )

    for _ in range(4):
        length = rng.randint(0, max(1, n_states + 2))
        xs = _rand_list(length, axes.value_range, rng)
        queries.append(
            Query(input=xs, output=eval_fsm(spec, xs), tag=QueryTag.TYPICAL)
        )

    adversarial_inputs = [[0] * (n_states + 3), [1, -1] * (n_states + 1)]
    for xs in adversarial_inputs:
        queries.append(
            Query(input=xs, output=eval_fsm(spec, xs), tag=QueryTag.ADVERSARIAL)
        )

    return dedupe_queries(queries)
