import random

from genfxn.core.int32 import wrap_i32
from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.core.predicates import get_threshold
from genfxn.piecewise.eval import eval_piecewise
from genfxn.piecewise.models import Branch, PiecewiseSpec

# Condition kinds supported by query generation. This is the authoritative
# contract - validators should import this constant rather than duplicating.
SUPPORTED_CONDITION_KINDS: frozenset[str] = frozenset({"lt", "le"})


def _get_branch_threshold(
    branch: Branch,
    *,
    int32_wrap: bool,
) -> int:
    """Extract threshold from a branch's predicate.

    Only supports condition kinds in SUPPORTED_CONDITION_KINDS.
    Other predicate types will raise ValueError.
    """
    info = get_threshold(branch.condition)
    if info is None or info.kind not in SUPPORTED_CONDITION_KINDS:
        raise ValueError(
            f"Unsupported predicate for query generation: {branch.condition}"
        )
    if int32_wrap:
        return wrap_i32(info.value)
    return info.value


def generate_piecewise_queries(
    spec: PiecewiseSpec,
    value_range: tuple[int, int] = (-100, 100),
    rng: random.Random | None = None,
    *,
    int32_wrap: bool = True,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    queries: list[Query] = []
    lo, hi = value_range
    if lo > hi:
        raise ValueError(f"value_range: low ({lo}) must be <= high ({hi})")

    # Coverage queries: one per region
    coverage_points = _get_coverage_points(
        spec,
        lo,
        hi,
        int32_wrap=int32_wrap,
    )
    for x in coverage_points:
        queries.append(
            Query(
                input=x,
                output=eval_piecewise(spec, x, int32_wrap=int32_wrap),
                tag=QueryTag.COVERAGE,
            )
        )

    # Boundary queries: at and around thresholds
    for branch in spec.branches:
        t = _get_branch_threshold(branch, int32_wrap=int32_wrap)
        for offset in [-1, 0, 1]:
            x = t + offset
            if lo <= x <= hi:
                queries.append(
                    Query(
                        input=x,
                        output=eval_piecewise(spec, x, int32_wrap=int32_wrap),
                        tag=QueryTag.BOUNDARY,
                    )
                )

    # Typical queries: random points in range
    n_typical = max(3, len(spec.branches) + 1)
    for _ in range(n_typical):
        x = rng.randint(lo, hi)
        queries.append(
            Query(
                input=x,
                output=eval_piecewise(spec, x, int32_wrap=int32_wrap),
                tag=QueryTag.TYPICAL,
            )
        )

    # Adversarial queries: extremes and special values
    adversarial_points = [lo, hi, 0, -1, 1]
    for x in adversarial_points:
        if lo <= x <= hi:
            queries.append(
                Query(
                    input=x,
                    output=eval_piecewise(spec, x, int32_wrap=int32_wrap),
                    tag=QueryTag.ADVERSARIAL,
                )
            )

    return dedupe_queries(queries)


def _get_coverage_points(
    spec: PiecewiseSpec,
    lo: int,
    hi: int,
    *,
    int32_wrap: bool,
) -> list[int]:
    if not spec.branches:
        return [(lo + hi) // 2]

    sorted_branches = sorted(
        spec.branches,
        key=lambda branch: _get_branch_threshold(
            branch,
            int32_wrap=int32_wrap,
        ),
    )
    points = []

    first_thresh = _get_branch_threshold(
        sorted_branches[0],
        int32_wrap=int32_wrap,
    )
    if lo < first_thresh:
        points.append((lo + first_thresh) // 2)

    for i in range(len(sorted_branches) - 1):
        t1 = _get_branch_threshold(
            sorted_branches[i],
            int32_wrap=int32_wrap,
        )
        t2 = _get_branch_threshold(
            sorted_branches[i + 1],
            int32_wrap=int32_wrap,
        )
        points.append((t1 + t2) // 2)

    last_thresh = _get_branch_threshold(
        sorted_branches[-1],
        int32_wrap=int32_wrap,
    )
    if last_thresh < hi:
        points.append((last_thresh + hi) // 2)

    return [p for p in points if lo <= p <= hi]
