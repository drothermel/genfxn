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
    seen_inputs: set[tuple[int, ...]] = set()

    def _append_query(xs: list[int], tag: QueryTag) -> None:
        key = tuple(xs)
        if key in seen_inputs:
            return
        try:
            output = eval_fsm(spec, xs)
        except ValueError:
            return
        seen_inputs.add(key)
        queries.append(Query(input=xs, output=output, tag=tag))

    coverage_inputs = [
        [],
        [v_lo],
        [v_hi],
        [0],
        _rand_list(4, axes.value_range, rng),
    ]
    for xs in coverage_inputs:
        _append_query(xs, QueryTag.COVERAGE)

    boundary_inputs = [
        [v_lo] * 3,
        [v_hi] * 3,
        [v_lo, v_hi, v_lo, v_hi],
    ]
    for xs in boundary_inputs:
        _append_query(xs, QueryTag.BOUNDARY)

    typical_target = 4
    typical_count = 0
    attempts = 0
    while typical_count < typical_target:
        attempts += 1
        if attempts > 80:
            break
        length = rng.randint(0, max(1, n_states + 2))
        xs = _rand_list(length, axes.value_range, rng)
        before = len(queries)
        _append_query(xs, QueryTag.TYPICAL)
        if len(queries) > before:
            typical_count += 1

    adversarial_inputs = [[0] * (n_states + 3), [1, -1] * (n_states + 1)]
    for xs in adversarial_inputs:
        _append_query(xs, QueryTag.ADVERSARIAL)

    if not any(q.tag == QueryTag.ADVERSARIAL for q in queries):
        for _ in range(40):
            length = rng.randint(max(1, n_states), n_states + 4)
            xs = _rand_list(length, axes.value_range, rng)
            before = len(queries)
            _append_query(xs, QueryTag.ADVERSARIAL)
            if len(queries) > before:
                break

    return dedupe_queries(queries)
