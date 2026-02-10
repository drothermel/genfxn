#!/usr/bin/env python
"""Calibrate intervals difficulty targeting and suite quota coverage."""

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, cast

import typer

from genfxn.core.presets import get_difficulty_axes
from genfxn.intervals.models import IntervalsAxes
from genfxn.intervals.task import generate_intervals_task
from genfxn.suites.generate import generate_suite, quota_report

app = typer.Typer(help="Calibrate intervals difficulty targeting.")

FAMILY = "intervals"
DIFFICULTIES = (1, 2, 3, 4, 5)
STRICT_EXACT_MIN = 0.50
STRICT_WITHIN_ONE_MIN = 0.90


def _difficulty_label(difficulty: int) -> str:
    return f"D{difficulty}"


def _compute_reachability(
    *,
    samples: int,
    seed: int,
) -> dict[int, dict[str, Any]]:
    results: dict[int, dict[str, Any]] = {}

    for difficulty in DIFFICULTIES:
        rng = random.Random(seed + difficulty * 1000)
        observed: list[int] = []

        for _ in range(samples):
            axes = cast(
                IntervalsAxes,
                get_difficulty_axes(FAMILY, difficulty, rng=rng),
            )
            task = generate_intervals_task(axes=axes, rng=rng)
            if task.difficulty is None:
                raise RuntimeError(
                    "intervals task produced None difficulty "
                    "during calibration"
                )
            observed.append(task.difficulty)

        counts = Counter(observed)
        exact = counts.get(difficulty, 0) / samples
        within_one = (
            sum(
                1
                for observed_difficulty in observed
                if abs(observed_difficulty - difficulty) <= 1
            )
            / samples
        )

        results[difficulty] = {
            "difficulty": difficulty,
            "samples": samples,
            "mean": sum(observed) / samples,
            "exact": exact,
            "within_one": within_one,
            "distribution": {
                str(score): count
                for score, count in sorted(counts.items())
            },
        }

    return results


def _check_monotonic_means(
    reachability: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    means = {
        difficulty: float(reachability[difficulty]["mean"])
        for difficulty in DIFFICULTIES
    }

    violations: list[dict[str, Any]] = []
    for previous, current in zip(DIFFICULTIES, DIFFICULTIES[1:], strict=False):
        previous_mean = means[previous]
        current_mean = means[current]
        if current_mean < previous_mean:
            violations.append(
                {
                    "from": _difficulty_label(previous),
                    "to": _difficulty_label(current),
                    "from_mean": previous_mean,
                    "to_mean": current_mean,
                }
            )

    return {
        "means": {
            _difficulty_label(difficulty): means[difficulty]
            for difficulty in DIFFICULTIES
        },
        "is_monotonic": not violations,
        "violations": violations,
    }


def _run_suite_checks(
    *,
    seed: int,
    pool_size: int,
) -> dict[int, dict[str, Any]]:
    checks: dict[int, dict[str, Any]] = {}

    for difficulty in DIFFICULTIES:
        suite_seed = seed + difficulty * 10_000

        try:
            tasks = generate_suite(
                family=FAMILY,
                difficulty=difficulty,
                seed=suite_seed,
                pool_size=pool_size,
            )
            rows = quota_report(tasks, FAMILY, difficulty)
        except (
            ValueError,
            RuntimeError,
        ) as exc:  # pragma: no cover - runtime script fallback
            checks[difficulty] = {
                "difficulty": difficulty,
                "seed": suite_seed,
                "generated_count": 0,
                "error": str(exc),
                "quota_rows": [],
                "under_rows": [],
            }
            continue

        quota_rows = [
            {
                "axis": axis,
                "value": value,
                "target": target,
                "achieved": achieved,
                "status": status,
            }
            for axis, value, target, achieved, status in rows
        ]
        under_rows = [row for row in quota_rows if row["status"] == "UNDER"]

        checks[difficulty] = {
            "difficulty": difficulty,
            "seed": suite_seed,
            "generated_count": len(tasks),
            "error": None,
            "quota_rows": quota_rows,
            "under_rows": under_rows,
        }

    return checks


def _strict_summary(
    *,
    enabled: bool,
    reachability: dict[int, dict[str, Any]],
    monotonic: dict[str, Any],
    suite_checks: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []

    for difficulty in DIFFICULTIES:
        stats = reachability[difficulty]
        exact = float(stats["exact"])
        within_one = float(stats["within_one"])
        if exact < STRICT_EXACT_MIN:
            failures.append(
                f"{_difficulty_label(difficulty)} exact={exact:.3f} "
                f"<{STRICT_EXACT_MIN:.2f}"
            )
        if within_one < STRICT_WITHIN_ONE_MIN:
            failures.append(
                f"{_difficulty_label(difficulty)} within_one={within_one:.3f} "
                f"<{STRICT_WITHIN_ONE_MIN:.2f}"
            )

        suite = suite_checks[difficulty]
        if suite["error"] is not None:
            failures.append(
                f"{_difficulty_label(difficulty)} suite failure: "
                f"{suite['error']}"
            )
        else:
            under_rows = cast(list[dict[str, Any]], suite["under_rows"])
            if under_rows:
                failures.append(
                    f"{_difficulty_label(difficulty)} has "
                    f"{len(under_rows)} UNDER quota rows"
                )

    if not bool(monotonic.get("is_monotonic", False)):
        failures.append("Monotonic means check failed")

    return {
        "enabled": enabled,
        "thresholds": {
            "exact_min": STRICT_EXACT_MIN,
            "within_one_min": STRICT_WITHIN_ONE_MIN,
            "under_rows_allowed": 0,
            "monotonic_required": True,
        },
        "passed": not failures,
        "failures": failures,
    }


@app.command()
def main(
    output: Path = typer.Option(
        Path("artifacts/intervals_calibration.json"),
        "--output",
        "-o",
        help="Path for calibration JSON report",
    ),
    samples: int = typer.Option(
        200,
        "--samples",
        "-n",
        min=1,
        help="Samples per targeted difficulty",
    ),
    seed: int = typer.Option(42, help="Base random seed"),
    pool_size: int = typer.Option(
        3000,
        help="Candidate pool size for suite generation",
    ),
    strict: bool = typer.Option(
        False,
        "--strict",
        help=(
            "Exit non-zero unless exact>=0.50, within_one>=0.90, "
            "monotonic means pass, and quota rows have no UNDER status"
        ),
    ),
) -> None:
    """Run intervals calibration checks and write a JSON report."""
    reachability = _compute_reachability(samples=samples, seed=seed)
    monotonic = _check_monotonic_means(reachability)
    suite_checks = _run_suite_checks(seed=seed, pool_size=pool_size)
    strict_report = _strict_summary(
        enabled=strict,
        reachability=reachability,
        monotonic=monotonic,
        suite_checks=suite_checks,
    )

    report = {
        "family": FAMILY,
        "difficulties": [
            _difficulty_label(difficulty) for difficulty in DIFFICULTIES
        ],
        "samples_per_difficulty": samples,
        "seed": seed,
        "pool_size": pool_size,
        "reachability": {
            _difficulty_label(difficulty): reachability[difficulty]
            for difficulty in DIFFICULTIES
        },
        "monotonic_means": monotonic,
        "suite_quota_checks": {
            _difficulty_label(difficulty): suite_checks[difficulty]
            for difficulty in DIFFICULTIES
        },
        "strict": strict_report,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    typer.echo(f"Wrote calibration report to {output}")
    for difficulty in DIFFICULTIES:
        stats = reachability[difficulty]
        typer.echo(
            f"{_difficulty_label(difficulty)}: mean={stats['mean']:.3f}, "
            f"exact={stats['exact']:.3f}, "
            f"within_one={stats['within_one']:.3f}"
        )

    if monotonic["is_monotonic"]:
        typer.echo("Monotonic means: OK")
    else:
        typer.echo("Monotonic means: FAIL")
        for violation in cast(list[dict[str, Any]], monotonic["violations"]):
            typer.echo(
                f"  {violation['from']} ({violation['from_mean']:.3f}) > "
                f"{violation['to']} ({violation['to_mean']:.3f})"
            )

    for difficulty in DIFFICULTIES:
        suite = suite_checks[difficulty]
        label = _difficulty_label(difficulty)
        if suite["error"] is not None:
            typer.echo(f"{label} suite: FAIL ({suite['error']})")
            continue

        under_count = len(cast(list[dict[str, Any]], suite["under_rows"]))
        typer.echo(
            f"{label} suite: generated={suite['generated_count']} "
            f"under_rows={under_count}"
        )

    if strict:
        if strict_report["passed"]:
            typer.echo("Strict checks: PASS")
        else:
            typer.echo("Strict checks: FAIL")
            for failure in cast(list[str], strict_report["failures"]):
                typer.echo(f"  - {failure}")
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
