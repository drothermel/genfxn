#!/usr/bin/env python
"""Phase 3 Demo: Stateful iteration functions (list[int] -> int).

This demo shows the complete pipeline for generating stateful iterator functions:
  1. Three template types: ConditionalLinearSum, ResettingBestPrefixSum, LongestRun
  2. Each template uses predicates and transforms from the core DSL
  3. Generated functions iterate over lists with accumulator state

Run with: uv run python scripts/demo_phase3_stateful.py
"""

import random

import srsly

from genfxn.stateful.models import StatefulAxes, TemplateType
from genfxn.stateful.task import generate_stateful_task


def main() -> None:
    print("=" * 70)
    print("Phase 3 Demo: Stateful Iteration Functions")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEMPLATE OVERVIEW
    # -------------------------------------------------------------------------
    print("""
--- Template Types ---

Stateful functions iterate over list[int] and return int. Three templates:

1. ConditionalLinearSum
   - Accumulates values with predicate-based transforms
   - If predicate(x): acc += true_transform(x)
   - Else: acc += false_transform(x)

2. ResettingBestPrefixSum
   - Tracks running sum that resets on predicate match
   - Maintains best (max) sum seen
   - Classic "maximum subarray" variant

3. LongestRun
   - Counts longest consecutive run matching predicate
   - Tracks current run length and max run length
""")

    # -------------------------------------------------------------------------
    # GENERATE ONE TASK PER TEMPLATE
    # -------------------------------------------------------------------------
    print("--- Generated Tasks (one per template) ---\n")

    for template in TemplateType:
        print("-" * 60)
        print(f"Template: {template.value}")
        print("-" * 60)

        axes = StatefulAxes(templates=[template])
        rng = random.Random(42)
        task = generate_stateful_task(axes, rng)

        print(f"\nTask ID: {task.task_id}")

        # Show the generated code
        print("\nGenerated Code:")
        print(task.code)

        # Show spec
        print("\nSpec (JSON):")
        print(srsly.json_dumps(task.spec, indent=2))

        # Show sample queries
        print("\nSample Queries:")
        for q in task.queries[:5]:
            input_str = str(q.input)
            if len(input_str) > 40:
                input_str = input_str[:37] + "..."
            print(f"  [{q.tag.value:12}] f({input_str}) = {q.output}")

        if len(task.queries) > 5:
            print(f"  ... and {len(task.queries) - 5} more queries")

        # Verify roundtrip
        namespace: dict = {}
        exec(task.code, namespace)  # noqa: S102
        f = namespace["f"]

        errors = []
        for q in task.queries:
            actual = f(q.input)
            if actual != q.output:
                errors.append(f"f({q.input}): expected {q.output}, got {actual}")

        if errors:
            print("\nVERIFICATION ERRORS:")
            for e in errors[:3]:
                print(f"  {e}")
        else:
            print(f"\nVerification: All {len(task.queries)} queries passed!")

        print()

    # -------------------------------------------------------------------------
    # AXES CONFIGURATION EXAMPLE
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("Axes Configuration Example")
    print("=" * 60)

    print("""
StatefulAxes controls the generation space:

  templates:         Which template types to sample from
  predicate_types:   Which predicate kinds (even, odd, lt, gt, etc.)
  transform_types:   Which transforms (identity, abs, shift, scale, negate)
  value_range:       Range for list element values
  list_length_range: Range for generated test list lengths
  threshold_range:   Range for comparison thresholds
  divisor_range:     Range for modular predicates
  shift_range:       Range for shift transform offsets
  scale_range:       Range for scale transform factors
""")

    # Generate with restricted axes
    print("Generating with restricted axes (even/odd predicates only):")
    from genfxn.core.predicates import PredicateType
    from genfxn.core.transforms import TransformType

    axes = StatefulAxes(
        templates=[TemplateType.CONDITIONAL_LINEAR_SUM],
        predicate_types=[PredicateType.EVEN, PredicateType.ODD],
        transform_types=[TransformType.IDENTITY, TransformType.NEGATE],
        value_range=(-20, 20),
        list_length_range=(3, 10),
    )

    task = generate_stateful_task(axes, random.Random(123))
    print(f"\nTask ID: {task.task_id}")
    print("\nGenerated Code:")
    print(task.code)

    print("\n" + "=" * 70)
    print("Phase 3 Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
