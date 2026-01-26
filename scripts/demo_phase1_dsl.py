#!/usr/bin/env python
"""Phase 1 Demo: Core DSL infrastructure.

This demo shows the building blocks that both function families (piecewise and
stateful) use: predicates, transforms, task IDs, and test rendering.

Run with: uv run python scripts/demo_phase1_dsl.py
"""

from genfxn.core.codegen import render_tests, task_id_from_spec
from genfxn.core.models import Query, QueryTag
from genfxn.core.predicates import (
    PredicateEven,
    PredicateGt,
    PredicateModEq,
    eval_predicate,
    render_predicate,
)
from genfxn.core.transforms import (
    TransformAbs,
    TransformClip,
    TransformShift,
    eval_transform,
    render_transform,
)


def main() -> None:
    print("=" * 70)
    print("Phase 1 Demo: Core DSL Infrastructure")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # PREDICATES
    # -------------------------------------------------------------------------
    print("""
--- Predicates ---

Predicates are boolean conditions on integers. They're used in:
  - Piecewise functions: to decide which branch to take
  - Stateful functions: to decide whether to apply a transform

Each predicate can be:
  - Evaluated: predicate(x) -> True/False
  - Rendered: predicate -> Python code string

Below we create three predicates and show how they evaluate on test values.
The format is: x->result (e.g., "3->True" means predicate(3) returns True)
""")

    predicates = [
        ("even", PredicateEven()),
        ("x > 10", PredicateGt(value=10)),
        ("x % 3 == 0 (divisible by 3)", PredicateModEq(divisor=3, remainder=0)),
    ]

    test_values = [-5, 0, 3, 9, 12, 15]

    for name, pred in predicates:
        rendered = render_predicate(pred)
        print(f"Predicate: {name}")
        print(f"  Rendered code: {rendered}")
        results = [f"{x}->{eval_predicate(pred, x)}" for x in test_values]
        print(f"  Evaluations:   {', '.join(results)}")
        print()

    # -------------------------------------------------------------------------
    # TRANSFORMS
    # -------------------------------------------------------------------------
    print("""--- Transforms ---

Transforms map integers to integers. They're used in stateful functions
to modify values before accumulating them.

Each transform can be:
  - Evaluated: transform(x) -> int
  - Rendered: transform -> Python code string

Below we show three transforms and their effect on test values.
""")

    transforms = [
        ("absolute value", TransformAbs()),
        ("shift by +5", TransformShift(offset=5)),
        ("clip to [0, 10]", TransformClip(low=0, high=10)),
    ]

    for name, t in transforms:
        rendered = render_transform(t)
        print(f"Transform: {name}")
        print(f"  Rendered code: {rendered}")
        results = [f"{x}->{eval_transform(t, x)}" for x in test_values]
        print(f"  Evaluations:   {', '.join(results)}")
        print()

    # -------------------------------------------------------------------------
    # TASK IDs
    # -------------------------------------------------------------------------
    print("""--- Task ID Generation ---

Each task gets a deterministic ID based on its spec. This ensures:
  - Same spec always produces the same ID (reproducibility)
  - Different specs produce different IDs (uniqueness)
  - IDs are prefixed with the family name for easy identification

The ID is a SHA-256 hash of the JSON-serialized spec (first 8 bytes, hex).
""")

    spec1 = {"n_branches": 2, "expr_types": ["affine", "quadratic"]}
    spec2 = {"n_branches": 3, "expr_types": ["affine"]}

    print(f"Spec 1: {spec1}")
    print(f"  ID: {task_id_from_spec('piecewise', spec1)}")
    print(f"Spec 2: {spec2}")
    print(f"  ID: {task_id_from_spec('piecewise', spec2)}")
    print()

    # -------------------------------------------------------------------------
    # RENDER TESTS
    # -------------------------------------------------------------------------
    print("""--- Render Tests ---

Queries are input/output pairs with tags indicating their purpose:
  - typical: random inputs from the normal range
  - boundary: inputs at or near decision boundaries
  - coverage: inputs that exercise each code path
  - adversarial: edge cases (extremes, zero, etc.)

render_tests() converts queries into Python assert statements for validation.
""")

    queries = [
        Query(input=5, output=10, tag=QueryTag.TYPICAL),
        Query(input=-3, output=3, tag=QueryTag.BOUNDARY),
        Query(input=100, output=10, tag=QueryTag.ADVERSARIAL),
    ]

    print("Queries:")
    for q in queries:
        print(f"  {q.tag.value}: input={q.input}, output={q.output}")
    print()
    print("Rendered as test assertions:")
    rendered_tests = render_tests("my_func", queries)
    for line in rendered_tests.split("\n"):
        print(f"  {line}")

    print("\n" + "=" * 70)
    print("Phase 1 Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
