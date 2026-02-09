from dataclasses import dataclass

from genfxn.sequence_dp.models import (
    OutputMode,
    PredicateAbsDiffLe,
    PredicateEq,
    PredicateModEq,
    SequenceDpPredicate,
    SequenceDpSpec,
    TemplateType,
    TieBreakOrder,
)

_TIE_BREAK_MOVES: dict[TieBreakOrder, tuple[str, str, str]] = {
    TieBreakOrder.DIAG_UP_LEFT: ("diag", "up", "left"),
    TieBreakOrder.DIAG_LEFT_UP: ("diag", "left", "up"),
    TieBreakOrder.UP_DIAG_LEFT: ("up", "diag", "left"),
    TieBreakOrder.UP_LEFT_DIAG: ("up", "left", "diag"),
    TieBreakOrder.LEFT_DIAG_UP: ("left", "diag", "up"),
    TieBreakOrder.LEFT_UP_DIAG: ("left", "up", "diag"),
}


@dataclass(frozen=True)
class _Cell:
    score: int
    alignment_len: int
    gap_count: int


def _predicate_matches(
    predicate: SequenceDpPredicate, a_value: int, b_value: int
) -> bool:
    if isinstance(predicate, PredicateEq):
        return a_value == b_value
    if isinstance(predicate, PredicateAbsDiffLe):
        return abs(a_value - b_value) <= predicate.max_diff
    if isinstance(predicate, PredicateModEq):
        return (a_value - b_value) % predicate.divisor == predicate.remainder
    raise ValueError(f"Unsupported predicate: {predicate}")


def _advance(prev: _Cell, delta: int, *, is_gap: bool) -> _Cell:
    return _Cell(
        score=prev.score + delta,
        alignment_len=prev.alignment_len + 1,
        gap_count=prev.gap_count + (1 if is_gap else 0),
    )


def _pick_step(
    tie_break: TieBreakOrder,
    diag: _Cell,
    up: _Cell,
    left: _Cell,
) -> _Cell:
    candidates = {"diag": diag, "up": up, "left": left}
    best_score = max(diag.score, up.score, left.score)
    for move in _TIE_BREAK_MOVES[tie_break]:
        candidate = candidates[move]
        if candidate.score == best_score:
            return candidate
    raise RuntimeError("unreachable tie-break state")


def _eval_global(spec: SequenceDpSpec, a: list[int], b: list[int]) -> _Cell:
    n = len(a)
    m = len(b)
    dp = [[_Cell(0, 0, 0) for _ in range(m + 1)] for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = _advance(dp[i - 1][0], spec.gap_score, is_gap=True)
    for j in range(1, m + 1):
        dp[0][j] = _advance(dp[0][j - 1], spec.gap_score, is_gap=True)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            is_match = _predicate_matches(
                spec.match_predicate, a[i - 1], b[j - 1]
            )
            diag_delta = spec.match_score if is_match else spec.mismatch_score
            diag = _advance(dp[i - 1][j - 1], diag_delta, is_gap=False)
            up = _advance(dp[i - 1][j], spec.gap_score, is_gap=True)
            left = _advance(dp[i][j - 1], spec.gap_score, is_gap=True)
            dp[i][j] = _pick_step(spec.step_tie_break, diag, up, left)

    return dp[n][m]


def _eval_local(spec: SequenceDpSpec, a: list[int], b: list[int]) -> _Cell:
    n = len(a)
    m = len(b)
    zero = _Cell(0, 0, 0)
    dp = [[zero for _ in range(m + 1)] for _ in range(n + 1)]
    best = zero

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            is_match = _predicate_matches(
                spec.match_predicate, a[i - 1], b[j - 1]
            )
            diag_delta = spec.match_score if is_match else spec.mismatch_score
            diag = _advance(dp[i - 1][j - 1], diag_delta, is_gap=False)
            up = _advance(dp[i - 1][j], spec.gap_score, is_gap=True)
            left = _advance(dp[i][j - 1], spec.gap_score, is_gap=True)
            chosen = _pick_step(spec.step_tie_break, diag, up, left)

            # Local alignment includes an explicit zero/reset candidate.
            if chosen.score <= 0:
                dp[i][j] = zero
            else:
                dp[i][j] = chosen

            # Strictly greater keeps earliest endpoint under row-major scan.
            if dp[i][j].score > best.score:
                best = dp[i][j]

    return best


def eval_sequence_dp(spec: SequenceDpSpec, a: list[int], b: list[int]) -> int:
    if spec.template == TemplateType.GLOBAL:
        cell = _eval_global(spec, a, b)
    else:
        cell = _eval_local(spec, a, b)

    if spec.output_mode == OutputMode.SCORE:
        return cell.score
    if spec.output_mode == OutputMode.ALIGNMENT_LEN:
        return cell.alignment_len
    return cell.gap_count
