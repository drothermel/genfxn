from genfxn.sequence_dp.models import SequenceDpSpec, TieBreakOrder

_TIE_BREAK_MOVES: dict[TieBreakOrder, tuple[str, str, str]] = {
    TieBreakOrder.DIAG_UP_LEFT: ("diag", "up", "left"),
    TieBreakOrder.DIAG_LEFT_UP: ("diag", "left", "up"),
    TieBreakOrder.UP_DIAG_LEFT: ("up", "diag", "left"),
    TieBreakOrder.UP_LEFT_DIAG: ("up", "left", "diag"),
    TieBreakOrder.LEFT_DIAG_UP: ("left", "diag", "up"),
    TieBreakOrder.LEFT_UP_DIAG: ("left", "up", "diag"),
}


def _long_literal(value: int) -> str:
    if value == -(1 << 63):
        return "Long.MIN_VALUE"
    return f"{value}L"


def render_sequence_dp(
    spec: SequenceDpSpec,
    func_name: str = "f",
    a_var: str = "a",
    b_var: str = "b",
) -> str:
    tie_break = _TIE_BREAK_MOVES[spec.step_tie_break]
    tie_values = ", ".join(f'"{move}"' for move in tie_break)

    predicate = spec.match_predicate.model_dump()
    kind = predicate["kind"]
    max_diff = int(predicate.get("max_diff", 0))
    divisor = int(predicate.get("divisor", 1))
    remainder = int(predicate.get("remainder", 0))

    lines = [
        (
            f"public static long {func_name}(long[] {a_var}, "
            f"long[] {b_var}) {{"
        ),
        f'    String template = "{spec.template.value}";',
        f'    String outputMode = "{spec.output_mode.value}";',
        f'    String predicateKind = "{kind}";',
        f"    long maxDiff = {_long_literal(max_diff)};",
        f"    long divisor = {_long_literal(divisor)};",
        f"    long remainder = {_long_literal(remainder)};",
        f"    long matchScore = {_long_literal(spec.match_score)};",
        f"    long mismatchScore = {_long_literal(spec.mismatch_score)};",
        f"    long gapScore = {_long_literal(spec.gap_score)};",
        "    String[] tieOrder = new String[] {" + tie_values + "};",
        "",
        f"    int n = {a_var}.length;",
        f"    int m = {b_var}.length;",
        "    long[][][] dp = new long[n + 1][m + 1][3];",
        "",
        "    if (template.equals(\"global\")) {",
        "        for (int i = 1; i <= n; i++) {",
        "            long[] prev = dp[i - 1][0];",
        "            dp[i][0] = new long[] {",
        "                prev[0] + gapScore,",
        "                prev[1] + 1L,",
        "                prev[2] + 1L,",
        "            };",
        "        }",
        "        for (int j = 1; j <= m; j++) {",
        "            long[] prev = dp[0][j - 1];",
        "            dp[0][j] = new long[] {",
        "                prev[0] + gapScore,",
        "                prev[1] + 1L,",
        "                prev[2] + 1L,",
        "            };",
        "        }",
        "    }",
        "",
        "    long[] zero = new long[] {0L, 0L, 0L};",
        "    long[] best = zero;",
        "",
        "    for (int i = 1; i <= n; i++) {",
        "        for (int j = 1; j <= m; j++) {",
        f"            long ai = {a_var}[i - 1];",
        f"            long bj = {b_var}[j - 1];",
        "            boolean isMatch;",
        "            if (predicateKind.equals(\"eq\")) {",
        "                isMatch = ai == bj;",
        "            } else if (predicateKind.equals(\"abs_diff_le\")) {",
        "                long absDiff = ai >= bj ? (ai - bj) : (bj - ai);",
        "                isMatch = Long.compareUnsigned(",
        "                    absDiff, maxDiff",
        "                ) <= 0;",
        "            } else {",
        "                isMatch = Math.floorMod(ai - bj, divisor) == "
        "remainder;",
        "            }",
        "",
        "            long[] prevDiag = dp[i - 1][j - 1];",
        "            long delta = isMatch ? matchScore : mismatchScore;",
        "            long[] diag = new long[] {",
        "                prevDiag[0] + delta,",
        "                prevDiag[1] + 1L,",
        "                prevDiag[2],",
        "            };",
        "",
        "            long[] prevUp = dp[i - 1][j];",
        "            long[] up = new long[] {",
        "                prevUp[0] + gapScore,",
        "                prevUp[1] + 1L,",
        "                prevUp[2] + 1L,",
        "            };",
        "",
        "            long[] prevLeft = dp[i][j - 1];",
        "            long[] left = new long[] {",
        "                prevLeft[0] + gapScore,",
        "                prevLeft[1] + 1L,",
        "                prevLeft[2] + 1L,",
        "            };",
        "",
        "            long bestScore = Math.max(",
        "                diag[0],",
        "                Math.max(up[0], left[0])",
        "            );",
        "            long[] chosen = diag;",
        "            for (String move : tieOrder) {",
        "                long[] candidate;",
        "                if (move.equals(\"diag\")) {",
        "                    candidate = diag;",
        "                } else if (move.equals(\"up\")) {",
        "                    candidate = up;",
        "                } else {",
        "                    candidate = left;",
        "                }",
        "                if (candidate[0] == bestScore) {",
        "                    chosen = candidate;",
        "                    break;",
        "                }",
        "            }",
        "",
        "            if (template.equals(\"local\") && chosen[0] <= 0L) {",
        "                dp[i][j] = zero;",
        "            } else {",
        "                dp[i][j] = chosen;",
        "            }",
        "",
        (
            "            if (template.equals(\"local\") && "
            "dp[i][j][0] > best[0]) {"
        ),
        "                best = dp[i][j];",
        "            }",
        "        }",
        "    }",
        "",
        "    long[] result;",
        "    if (template.equals(\"global\")) {",
        "        result = dp[n][m];",
        "    } else {",
        "        result = best;",
        "    }",
        "",
        "    if (outputMode.equals(\"score\")) {",
        "        return result[0];",
        "    }",
        "    if (outputMode.equals(\"alignment_len\")) {",
        "        return result[1];",
        "    }",
        "    return result[2];",
        "}",
    ]
    return "\n".join(lines)
