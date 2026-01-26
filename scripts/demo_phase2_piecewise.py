#!/usr/bin/env python
"""Phase 2 Demo: Piecewise numeric functions.

This demo shows the complete pipeline for generating piecewise int->int functions:
  1. Define axes (configuration for what kinds of functions to generate)
  2. Sample a spec (the mathematical definition of a specific function)
  3. Render to Python code
  4. Generate test queries with different coverage strategies
  5. Package everything into a Task for the dataset

Run with: uv run python scripts/demo_phase2_piecewise.py
"""

import random

import srsly

from genfxn.piecewise.models import ExprType, PiecewiseAxes
from genfxn.piecewise.task import generate_piecewise_task


def main() -> None:
    print("=" * 70)
    print("Phase 2 Demo: Piecewise Numeric Functions")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # AXES CONFIGURATION
    # -------------------------------------------------------------------------
    print("""
--- Axes Configuration ---

"Axes" define the space of possible functions we can generate. Think of them
as the knobs you can turn to control complexity:

  - n_branches: How many if/elif branches (more = more complex logic)
  - expr_types: What math expressions to use in each branch
      - affine: a*x + b (linear)
      - quadratic: a*x^2 + b*x + c
      - abs: a*|x| + b
      - mod: a*(x % d) + b
  - value_range: Input domain for test queries
  - coeff_range: Range for coefficients (a, b, c values)
  - threshold_range: Range for branch thresholds

Below we configure axes for 2-branch functions with affine/quadratic expressions.
""")

    axes = PiecewiseAxes(
        n_branches=2,
        expr_types=[ExprType.AFFINE, ExprType.QUADRATIC],
        value_range=(-50, 50),
        coeff_range=(-3, 3),
        threshold_range=(-20, 20),
    )

    print("Configuration:")
    print(f"  n_branches: {axes.n_branches}")
    print(f"  expr_types: {[e.value for e in axes.expr_types]}")
    print(f"  value_range: {axes.value_range}")
    print(f"  coeff_range: {axes.coeff_range}")
    print(f"  threshold_range: {axes.threshold_range}")

    # -------------------------------------------------------------------------
    # GENERATE A TASK
    # -------------------------------------------------------------------------
    print("""
--- Generated Task ---

A Task contains everything needed for training/evaluation:
  - task_id: Unique, deterministic identifier
  - family: "piecewise" or "stateful"
  - spec: The full mathematical specification (JSON-serializable)
  - code: Executable Python function
  - queries: Input/output pairs with coverage tags
""")

    rng = random.Random(42)  # Fixed seed for reproducibility
    task = generate_piecewise_task(axes, rng)

    print(f"Task ID: {task.task_id}")
    print(f"Family:  {task.family}")

    # -------------------------------------------------------------------------
    # GENERATED CODE
    # -------------------------------------------------------------------------
    print("""
--- Generated Code ---

The renderer converts the spec into clean, executable Python. Notice:
  - Proper if/elif/else structure
  - Type hints for clarity
  - Readable expressions (e.g., "2 * x - 1" not "2*x+-1")
""")

    print(task.code)

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------
    print("""
--- Queries ---

Queries test the function with strategic inputs. Each has a tag:

  coverage:    One input per branch region (ensures all paths tested)
  boundary:    Inputs at threshold-1, threshold, threshold+1 (edge cases)
  typical:     Random inputs from the value range
  adversarial: Extremes and special values (min, max, 0, -1, 1)

Format: [tag] f(input) = output
""")

    for q in task.queries[:12]:
        print(f"  [{q.tag.value:12}] f({q.input:4}) = {q.output}")

    if len(task.queries) > 12:
        print(f"  ... and {len(task.queries) - 12} more queries")

    # -------------------------------------------------------------------------
    # SPEC (JSON)
    # -------------------------------------------------------------------------
    print("""
--- Spec (JSON) ---

The spec is the source of truth. It contains:
  - branches: List of {condition (predicate), expr} for each branch
  - default_expr: Expression used when no branch matches

This is what gets hashed for the task_id and can recreate the function.
""")

    print(srsly.json_dumps(task.spec, indent=2))

    # -------------------------------------------------------------------------
    # FULL TASK (JSONL)
    # -------------------------------------------------------------------------
    print("""
--- Full Task (JSONL format) ---

This is the output format for the dataset. Each line is one complete task.
Use this for training data, evaluation sets, etc.
""")

    print(task.model_dump_json())

    # -------------------------------------------------------------------------
    # VERIFICATION
    # -------------------------------------------------------------------------
    print("""
--- Verification ---

We verify the pipeline by executing the generated code and checking that
all queries produce the expected outputs. This catches rendering bugs.
""")

    namespace: dict = {}
    exec(task.code, namespace) # noqa: S102
    f = namespace["f"]

    errors = []
    for q in task.queries:
        actual = f(q.input)
        if actual != q.output:
            errors.append(f"f({q.input}): expected {q.output}, got {actual}")

    if errors:
        print("ERRORS FOUND:")
        for e in errors:
            print(f"  {e}")
    else:
        print(f"All {len(task.queries)} queries verified correctly!")

    print("\n" + "=" * 70)
    print("Phase 2 Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
