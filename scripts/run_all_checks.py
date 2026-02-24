#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUFF_FIX_PATHS = ("src/", "tests/", "scripts/")

GENERATED_CODE_QUALITY_CMD = [
    "uv",
    "run",
    "python",
    "scripts/check_generated_code_quality.py",
    "--families",
    "all",
    "--seed",
    "42",
    "--count-per-family",
    "2",
    "--pool-size",
    "24",
]

FULL_TEST_CMD = [
    "uv",
    "run",
    "pytest",
    "tests/",
    "-v",
    "--verification-level=full",
    "-n",
    "auto",
    "--dist=worksteal",
]


def _run_command(cmd: Sequence[str]) -> int:
    printable = " ".join(shlex.quote(part) for part in cmd)
    print(f"$ {printable}", flush=True)
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def _run_step(name: str, cmd: Sequence[str]) -> int:
    print(f"\n== {name} ==", flush=True)
    rc = _run_command(cmd)
    if rc != 0:
        print(f"Step failed: {name}", file=sys.stderr, flush=True)
    return rc


def _has_changes(paths: Sequence[str]) -> bool:
    cmd = ["git", "diff", "--quiet", "--", *paths]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode != 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full repository checks: formatting, lint, type checks, "
            "generated Java/Rust quality checks, and full tests."
        )
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help=(
            "CI mode. Uses ruff format --check and fails if ruff --fix would "
            "modify src/tests/scripts."
        ),
    )
    args = parser.parse_args()

    format_cmd = (
        ["uv", "run", "ruff", "format", "--check", "."]
        if args.ci
        else ["uv", "run", "ruff", "format", "."]
    )

    steps = [
        ("Ruff format (all Python files)", format_cmd),
        (
            "Ruff check --fix (src/tests/scripts)",
            ["uv", "run", "ruff", "check", "--fix", *RUFF_FIX_PATHS],
        ),
        (
            "Ruff check (src blocking scope)",
            ["uv", "run", "ruff", "check", "src/"],
        ),
        ("Type check (src)", ["uv", "run", "ty", "check", "src"]),
        ("Generated code quality (Java/Rust)", GENERATED_CODE_QUALITY_CMD),
        ("Pytest full verification", FULL_TEST_CMD),
    ]

    for name, cmd in steps:
        rc = _run_step(name, cmd)
        if rc != 0:
            return rc

    if args.ci and _has_changes(RUFF_FIX_PATHS):
        print(
            (
                "CI mode failure: `ruff check --fix src/ tests/ scripts/` "
                "would modify files. "
                "Run `uv run python scripts/run_all_checks.py` "
                "locally and commit the resulting changes."
            ),
            file=sys.stderr,
            flush=True,
        )
        return 1

    print("\nAll checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
