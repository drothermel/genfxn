#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys

DEFAULT_BUDGETS = {
    "fast": 30.0,
    "standard": 90.0,
    "full": 180.0,
}

DEFAULT_WORKERS = {
    "fast": "auto",
    "standard": "auto",
    "full": "auto",
}


def _has_xdist() -> bool:
    return importlib.util.find_spec("xdist") is not None


def _parse_duration_seconds(output: str) -> float | None:
    matches = re.findall(r"in (\d+(?:\.\d+)?)s", output)
    if not matches:
        return None
    return float(matches[-1])


def _parse_workers(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "auto":
        return "auto"
    if normalized.isdigit():
        return str(int(normalized))
    raise argparse.ArgumentTypeError(
        "workers must be a non-negative integer or 'auto'"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run pytest with verification tiers, optional xdist workers, "
            "and optional runtime budget checks."
        )
    )
    parser.add_argument(
        "--tier",
        choices=("fast", "standard", "full"),
        default="full",
        help="Verification tier to run.",
    )
    parser.add_argument(
        "--workers",
        type=_parse_workers,
        default=None,
        help=(
            "xdist worker count or 'auto'. "
            "Defaults to machine-maximizing per-tier values."
        ),
    )
    parser.add_argument(
        "--durations",
        type=int,
        default=20,
        help="Number of slow tests to show.",
    )
    parser.add_argument(
        "--durations-min",
        type=float,
        default=0.05,
        help="Minimum duration threshold for slow test reporting.",
    )
    parser.add_argument(
        "--enforce-budget",
        action="store_true",
        help="Fail if total runtime exceeds budget for selected tier.",
    )
    parser.add_argument(
        "--budget-fast",
        type=float,
        default=DEFAULT_BUDGETS["fast"],
        help="Runtime budget in seconds for fast tier.",
    )
    parser.add_argument(
        "--budget-standard",
        type=float,
        default=DEFAULT_BUDGETS["standard"],
        help="Runtime budget in seconds for standard tier.",
    )
    parser.add_argument(
        "--budget-full",
        type=float,
        default=DEFAULT_BUDGETS["full"],
        help="Runtime budget in seconds for full tier.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed through to pytest.",
    )
    args = parser.parse_args()

    workers = args.workers
    if workers is None:
        workers = DEFAULT_WORKERS[args.tier]

    cmd = [
        "uv",
        "run",
        "pytest",
        "tests/",
        "-v",
        f"--verification-level={args.tier}",
        f"--durations={args.durations}",
        f"--durations-min={args.durations_min}",
    ]
    if _has_xdist():
        cmd.extend(["-n", str(workers)])
    if args.pytest_args:
        passthrough = (
            args.pytest_args[1:]
            if args.pytest_args[0] == "--"
            else args.pytest_args
        )
        cmd.extend(passthrough)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)

    if proc.returncode != 0:
        return proc.returncode

    if not args.enforce_budget:
        return 0

    duration = _parse_duration_seconds(proc.stdout + "\n" + proc.stderr)
    if duration is None:
        print(
            "Could not parse pytest runtime; skipping budget enforcement.",
            file=sys.stderr,
        )
        return 0

    budgets = {
        "fast": args.budget_fast,
        "standard": args.budget_standard,
        "full": args.budget_full,
    }
    budget = budgets[args.tier]
    if duration > budget:
        print(
            (
                f"Runtime budget exceeded for tier '{args.tier}': "
                f"{duration:.2f}s > {budget:.2f}s"
            ),
            file=sys.stderr,
        )
        return 2
    print(
        f"Runtime budget check passed for tier '{args.tier}': "
        f"{duration:.2f}s <= {budget:.2f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
