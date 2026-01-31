#!/usr/bin/env python
"""Analyze difficulty scoring formulas and generate compositional analysis.

This script analyzes the difficulty scoring functions and outputs:
1. Contribution tables showing each axis value → weighted contribution
2. All valid compositions for each difficulty level
3. Current preset accuracy (% of tasks hitting target difficulty)

Usage:
    uv run python scripts/analyze_difficulty.py
    uv run python scripts/analyze_difficulty.py --format markdown
    uv run python scripts/analyze_difficulty.py --family piecewise
    uv run python scripts/analyze_difficulty.py --verify-presets
"""

import random
from collections import Counter
from dataclasses import dataclass
from typing import Any, cast

import typer

from genfxn.core.presets import get_difficulty_axes, get_valid_difficulties
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stateful.models import StatefulAxes
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.models import StringRulesAxes
from genfxn.stringrules.task import generate_stringrules_task

app = typer.Typer(help="Analyze difficulty scoring and presets.")


@dataclass
class AxisContribution:
    """Represents an axis value and its weighted contribution."""

    axis: str
    value: str
    score: int
    weight: float
    contribution: float


@dataclass
class FamilyAnalysis:
    """Analysis results for a family."""

    family: str
    formula: str
    contributions: list[AxisContribution]
    max_raw: float
    min_raw: float
    achievable_difficulties: list[int]


# =============================================================================
# Scoring formulas (mirrored from difficulty.py for analysis)
# NOTE: Keep these in sync with the actual difficulty calculation logic.
# Consider importing from the source if refactoring to avoid duplication.
# =============================================================================

PIECEWISE_WEIGHTS = {"branches": 0.4, "expr_type": 0.4, "coeff": 0.2}

PIECEWISE_AXES = {
    "branches": [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)],
    "expr_type": [("AFFINE", 1), ("ABS", 2), ("MOD", 3), ("QUADRATIC", 4)],
    "coeff": [("≤1", 1), ("~2", 2), ("~3", 3), ("~4", 4), ("≥5", 5)],
}

STATEFUL_WEIGHTS = {"template": 0.4, "predicate": 0.3, "transform": 0.3}

STATEFUL_AXES = {
    "template": [
        ("LONGEST_RUN", 1),
        ("CONDITIONAL_LINEAR_SUM", 3),
        ("RESETTING_BEST_PREFIX_SUM", 4),
    ],
    "predicate": [
        ("EVEN/ODD", 1),
        ("LT/LE/GT/GE", 2),
        ("IN_SET", 3),
        ("MOD_EQ", 4),
    ],
    "transform": [("IDENTITY", 1), ("ABS/NEGATE", 2), ("SHIFT/SCALE", 3)],
}

SIMPLE_ALGORITHMS_WEIGHTS = {"template": 0.5, "mode": 0.3, "edge": 0.2}

SIMPLE_ALGORITHMS_AXES = {
    "template": [
        ("MOST_FREQUENT", 2),
        ("COUNT_PAIRS_SUM", 3),
        ("MAX_WINDOW_SUM", 3),
    ],
    "mode": [
        ("tie_break=SMALLEST", 1),
        ("tie_break=FIRST_SEEN", 2),
        ("counting=ALL_INDICES", 2),
        ("counting=UNIQUE_VALUES", 3),
        ("k≤2", 1),
        ("k=3-5", 2),
        ("k≥6", 3),
    ],
    "edge": [("zero default", 1), ("non-zero default", 2)],
}

STRINGRULES_WEIGHTS = {"rules": 0.4, "predicate": 0.3, "transform": 0.3}

STRINGRULES_AXES = {
    "rules": [(1, 1), (2, 2), (3, 3), (4, 4), ("5+", 5)],
    "predicate": [
        ("IS_*", 1),
        ("STARTS/ENDS/CONTAINS", 2),
        ("LENGTH_CMP eq/ne", 2),
        ("LENGTH_CMP lt/gt", 3),
    ],
    "transform": [
        ("IDENTITY", 1),
        ("LOWER/UPPER/REVERSE/...", 2),
        ("REPLACE/STRIP/...", 3),
    ],
}


def analyze_family(family: str) -> FamilyAnalysis:
    """Analyze difficulty contributions for a family."""
    if family == "piecewise":
        weights = PIECEWISE_WEIGHTS
        axes = PIECEWISE_AXES
        formula = (
            "raw = 0.4 × branch_score + 0.4 × expr_score + 0.2 × coeff_score"
        )
    elif family == "stateful":
        weights = STATEFUL_WEIGHTS
        axes = STATEFUL_AXES
        formula = "raw = 0.4 × template + 0.3 × predicate + 0.3 × transform_avg"
    elif family == "simple_algorithms":
        weights = SIMPLE_ALGORITHMS_WEIGHTS
        axes = SIMPLE_ALGORITHMS_AXES
        formula = "raw = 0.5 × template + 0.3 × mode + 0.2 × edge"
    elif family == "stringrules":
        weights = STRINGRULES_WEIGHTS
        axes = STRINGRULES_AXES
        formula = "raw = 0.4 × rule_count + 0.3 × pred_avg + 0.3 × trans_avg"
    else:
        raise ValueError(f"Unknown family: {family}")

    contributions = []
    for axis_name, values in axes.items():
        weight = weights[axis_name]
        for value, score in values:
            contrib = weight * score
            contributions.append(
                AxisContribution(
                    axis=axis_name,
                    value=str(value),
                    score=score,
                    weight=weight,
                    contribution=contrib,
                )
            )

    # Calculate min/max raw scores
    min_scores = {k: min(s for _, s in v) for k, v in axes.items()}
    max_scores = {k: max(s for _, s in v) for k, v in axes.items()}

    min_raw = sum(weights[k] * min_scores[k] for k in weights)
    max_raw = sum(weights[k] * max_scores[k] for k in weights)

    # Determine achievable difficulties
    achievable = []
    for d in range(1, 6):
        # Difficulty d is achievable if there's a raw score that rounds to d
        # Rounding: 0.5-1.49 → 1, 1.5-2.49 → 2, etc.
        low_bound = d - 0.5 if d > 1 else 0
        high_bound = d + 0.5
        if min_raw <= high_bound and max_raw >= low_bound:
            achievable.append(d)

    return FamilyAnalysis(
        family=family,
        formula=formula,
        contributions=contributions,
        min_raw=min_raw,
        max_raw=max_raw,
        achievable_difficulties=achievable,
    )


def format_plain(analysis: FamilyAnalysis) -> str:
    """Format analysis as plain text."""
    lines = [
        f"=== {analysis.family.upper()} ===",
        f"Formula: {analysis.formula}",
        f"Raw range: {analysis.min_raw:.1f} - {analysis.max_raw:.1f}",
        f"Achievable difficulties: {analysis.achievable_difficulties}",
        "",
        "Axis Contributions:",
    ]

    current_axis = None
    for c in analysis.contributions:
        if c.axis != current_axis:
            lines.append(f"  {c.axis} (weight={c.weight}):")
            current_axis = c.axis
        lines.append(
            f"    {c.value}: score={c.score} → contribution="
            f"{c.contribution:.1f}"
        )

    return "\n".join(lines)


def format_markdown(analysis: FamilyAnalysis) -> str:
    """Format analysis as markdown."""
    lines = [
        f"## {analysis.family.title()}",
        "",
        f"**Formula:** `{analysis.formula}`",
        "",
        f"**Raw range:** {analysis.min_raw:.1f} - {analysis.max_raw:.1f}",
        "",
        f"**Achievable difficulties:** {analysis.achievable_difficulties}",
        "",
        "### Axis Contributions",
        "",
        "| Axis | Value | Score | Weight | Contribution |",
        "|------|-------|-------|--------|--------------|",
    ]

    for c in analysis.contributions:
        row = (
            f"| {c.axis} | {c.value} | {c.score} | {c.weight} | "
            f"{c.contribution:.1f} |"
        )
        lines.append(row)

    return "\n".join(lines)


def verify_presets(
    family: str, n_samples: int = 50
) -> dict[int, dict[str, Any]]:
    """Verify preset accuracy for a family."""
    results: dict[int, dict[str, Any]] = {}

    for difficulty in get_valid_difficulties(family):
        rng = random.Random(42)
        difficulties = []

        for _ in range(n_samples):
            axes = get_difficulty_axes(family, difficulty, rng=rng)
            if family == "piecewise":
                task = generate_piecewise_task(
                    axes=cast(PiecewiseAxes, axes), rng=rng
                )
            elif family == "stateful":
                task = generate_stateful_task(
                    axes=cast(StatefulAxes, axes), rng=rng
                )
            elif family == "simple_algorithms":
                task = generate_simple_algorithms_task(
                    axes=cast(SimpleAlgorithmsAxes, axes), rng=rng
                )
            elif family == "stringrules":
                task = generate_stringrules_task(
                    axes=cast(StringRulesAxes, axes), rng=rng
                )
            else:
                raise ValueError(f"Unknown family: {family}")

            difficulties.append(task.difficulty)

        counts = Counter(difficulties)
        mean = sum(difficulties) / len(difficulties)
        exact_pct = counts.get(difficulty, 0) / n_samples * 100
        within_one = sum(1 for d in difficulties if abs(d - difficulty) <= 1)
        within_one_pct = within_one / n_samples * 100

        results[difficulty] = {
            "mean": mean,
            "exact_pct": exact_pct,
            "within_one_pct": within_one_pct,
            "distribution": dict(sorted(counts.items())),
        }

    return results


@app.command()
def analyze(
    family: str | None = typer.Option(
        None, "--family", "-f", help="Analyze specific family"
    ),
    output_format: str = typer.Option(
        "plain", "--format", help="Output format: plain or markdown"
    ),
    verify: bool = typer.Option(
        False, "--verify-presets", help="Verify preset accuracy"
    ),
    samples: int = typer.Option(
        50, "--samples", "-n", help="Number of samples for verification"
    ),
) -> None:
    """Analyze difficulty scoring and optionally verify presets."""
    families = (
        [family]
        if family
        else ["piecewise", "stateful", "simple_algorithms", "stringrules"]
    )

    for fam in families:
        analysis = analyze_family(fam)

        if output_format == "markdown":
            typer.echo(format_markdown(analysis))
        else:
            typer.echo(format_plain(analysis))

        if verify:
            typer.echo("\nPreset Verification:")
            results = verify_presets(fam, samples)
            for diff, data in sorted(results.items()):
                status = "✓" if data["exact_pct"] >= 70 else "✗"
                typer.echo(
                    f"  Difficulty {diff}: mean={data['mean']:.2f}, "
                    f"exact={data['exact_pct']:.0f}%, "
                    f"within±1={data['within_one_pct']:.0f}% {status}"
                )
                typer.echo(f"    Distribution: {data['distribution']}")

        typer.echo("")


if __name__ == "__main__":
    app()
