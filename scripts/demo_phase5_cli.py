#!/usr/bin/env python
"""Phase 5 Demo: CLI usage for task generation and splitting."""

import subprocess
import tempfile
from pathlib import Path


def run(cmd: str) -> None:
    """Run a command and print its output."""
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tasks = tmp / "tasks.jsonl"
        train = tmp / "train.jsonl"
        test = tmp / "test.jsonl"

        print("=" * 60)
        print("Phase 5 Demo: CLI Usage")
        print("=" * 60)

        # Generate tasks
        print("\n--- Generate tasks (all families) ---")
        run(f"uv run genfxn generate -o {tasks} -f all -n 50 -s 42")

        # Show info
        print("\n--- Show task info ---")
        run(f"uv run genfxn info {tasks}")

        # Split by template
        print("\n--- Split by template (hold out longest_run) ---")
        run(
            f"uv run genfxn split {tasks} "
            f"--train {train} --test {test} "
            f"--holdout-axis template --holdout-value longest_run"
        )
        run(f"uv run genfxn info {train}")
        run(f"uv run genfxn info {test}")

        # Generate piecewise only
        print("\n--- Generate piecewise tasks only ---")
        piecewise = tmp / "piecewise.jsonl"
        run(f"uv run genfxn generate -o {piecewise} -f piecewise -n 20 -s 123")
        run(f"uv run genfxn info {piecewise}")

        # Split by first branch threshold range
        print("\n--- Split by first branch threshold range (-10 to 10) ---")
        train2 = tmp / "train2.jsonl"
        test2 = tmp / "test2.jsonl"
        run(
            f"uv run genfxn split {piecewise} "
            f"--train {train2} --test {test2} "
            f"--holdout-axis branches.0.condition.value --holdout-value -10,10 --holdout-type range"
        )
        run(f"uv run genfxn info {train2}")
        run(f"uv run genfxn info {test2}")

        print("\n" + "=" * 60)
        print("Demo complete!")
        print("=" * 60)


if __name__ == "__main__":
    main()
