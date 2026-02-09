import random

from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.sequence_dp.models import SequenceDpAxes, SequenceDpSpec


def _rand_list(
    length: int,
    value_range: tuple[int, int],
    rng: random.Random,
) -> list[int]:
    lo, hi = value_range
    return [rng.randint(lo, hi) for _ in range(length)]


def _patterned_list(length: int, pattern: list[int]) -> list[int]:
    if length <= 0:
        return []
    return [pattern[idx % len(pattern)] for idx in range(length)]


def _query_input(a: list[int], b: list[int]) -> dict[str, list[int]]:
    return {"a": list(a), "b": list(b)}


def generate_sequence_dp_queries(
    spec: SequenceDpSpec,
    axes: SequenceDpAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    a_lo, a_hi = axes.len_a_range
    b_lo, b_hi = axes.len_b_range
    v_lo, v_hi = axes.value_range
    v_mid = (v_lo + v_hi) // 2

    queries: list[Query] = []
    seen_inputs: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()

    def _append_query(
        a_vals: list[int], b_vals: list[int], tag: QueryTag
    ) -> None:
        key = (tuple(a_vals), tuple(b_vals))
        if key in seen_inputs:
            return
        seen_inputs.add(key)
        queries.append(
            Query(
                input=_query_input(a_vals, b_vals),
                output=eval_sequence_dp(spec, a_vals, b_vals),
                tag=tag,
            )
        )

    coverage_inputs = [
        ([], []),
        ([v_mid], [v_mid]),
        ([], [v_mid]),
        ([v_mid], []),
    ]
    for a_vals, b_vals in coverage_inputs:
        _append_query(a_vals, b_vals, QueryTag.COVERAGE)

    boundary_inputs = [
        ([v_lo] * a_lo, [v_lo] * b_lo),
        ([v_hi] * a_hi, [v_hi] * b_hi),
        ([v_lo] * a_hi, [v_hi] * b_lo),
        ([v_hi] * a_lo, [v_lo] * b_hi),
    ]
    for a_vals, b_vals in boundary_inputs:
        _append_query(a_vals, b_vals, QueryTag.BOUNDARY)

    # Ensure at least one stable typical example, even when ranges collapse.
    typical_a_len = max(1, a_lo)
    typical_b_len = max(1, b_lo)
    _append_query(
        [v_mid + idx for idx in range(typical_a_len)],
        [v_mid - idx for idx in range(typical_b_len)],
        QueryTag.TYPICAL,
    )

    for _ in range(4):
        a_len = rng.randint(a_lo, a_hi)
        b_len = rng.randint(b_lo, b_hi)
        a_vals = _rand_list(a_len, axes.value_range, rng)
        b_vals = _rand_list(b_len, axes.value_range, rng)
        _append_query(a_vals, b_vals, QueryTag.TYPICAL)

    adv_a_len = max(a_lo, min(a_hi, 8))
    adv_b_len = max(b_lo, min(b_hi, 8))
    adversarial_inputs = [
        (
            _patterned_list(adv_a_len, [v_lo, v_hi, v_mid]),
            _patterned_list(adv_b_len, [v_hi, v_lo, v_mid]),
        ),
        (
            _patterned_list(max(a_lo, min(a_hi, 12)), [0, 1, -1]),
            _patterned_list(max(b_lo, min(b_hi, 3)), [0]),
        ),
    ]
    for a_vals, b_vals in adversarial_inputs:
        _append_query(a_vals, b_vals, QueryTag.ADVERSARIAL)

    for tag in QueryTag:
        if any(query.tag == tag for query in queries):
            continue
        tag_shift = list(QueryTag).index(tag) + 1
        _append_query(
            [v_mid + tag_shift + idx for idx in range(max(1, a_lo))],
            [v_mid - tag_shift - idx for idx in range(max(1, b_lo))],
            tag,
        )
        if any(query.tag == tag for query in queries):
            continue
        for _ in range(32):
            a_len = rng.randint(a_lo, a_hi)
            b_len = rng.randint(b_lo, b_hi)
            a_vals = _rand_list(a_len, axes.value_range, rng)
            b_vals = _rand_list(b_len, axes.value_range, rng)
            prev_count = len(queries)
            _append_query(a_vals, b_vals, tag)
            if len(queries) > prev_count:
                break

    return dedupe_queries(queries)
