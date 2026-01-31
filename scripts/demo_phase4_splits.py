#!/usr/bin/env python
"""Phase 4 Demo: Axis-heldout splits for generalization studies."""

from genfxn.piecewise.task import generate_piecewise_task
from genfxn.splits import AxisHoldout, HoldoutType, split_tasks
from genfxn.stateful.task import generate_stateful_task


def main() -> None:
    # Generate mixed dataset
    tasks = []
    for _ in range(25):
        tasks.append(generate_piecewise_task())
    for _ in range(25):
        tasks.append(generate_stateful_task())

    print(f"Generated {len(tasks)} tasks")
    print(f"  Piecewise: {sum(1 for t in tasks if t.family == 'piecewise')}")
    print(f"  Stateful: {sum(1 for t in tasks if t.family == 'stateful')}")

    # Example 1: Hold out a specific template
    holdouts = [
        AxisHoldout(
            axis_path="template",
            holdout_type=HoldoutType.EXACT,
            holdout_value="longest_run",
        ),
    ]
    result = split_tasks(tasks, holdouts)
    print("\nHoldout: template == 'longest_run'")
    print(f"  Train: {len(result.train)}, Test: {len(result.test)}")

    # Example 2: Hold out a predicate type (stateful)
    holdouts = [
        AxisHoldout(
            axis_path="predicate.kind",
            holdout_type=HoldoutType.EXACT,
            holdout_value="mod_eq",
        ),
    ]
    result = split_tasks(tasks, holdouts)
    print("\nHoldout: predicate.kind == 'mod_eq'")
    print(f"  Train: {len(result.train)}, Test: {len(result.test)}")

    # Example 3: Hold out piecewise condition types
    holdouts = [
        AxisHoldout(
            axis_path="branches.0.condition.kind",
            holdout_type=HoldoutType.EXACT,
            holdout_value="lt",
        ),
    ]
    result = split_tasks(tasks, holdouts)
    print("\nHoldout: branches.0.condition.kind == 'lt'")
    print(f"  Train: {len(result.train)}, Test: {len(result.test)}")

    # Example 4: Multiple holdouts (OR logic)
    holdouts = [
        AxisHoldout(
            axis_path="template",
            holdout_type=HoldoutType.EXACT,
            holdout_value="resetting_best_prefix_sum",
        ),
        AxisHoldout(
            axis_path="default_expr.kind",
            holdout_type=HoldoutType.EXACT,
            holdout_value="quadratic",
        ),
    ]
    result = split_tasks(tasks, holdouts)
    print(
        "\nHoldout: template == 'resetting_best_prefix_sum' OR "
        "default_expr.kind == 'quadratic'"
    )
    print(f"  Train: {len(result.train)}, Test: {len(result.test)}")

    # Show sample specs from test set
    if result.test:
        print("\n  Sample test task specs:")
        for task in result.test[:3]:
            template = task.spec.get("template", "N/A")
            default_expr = task.spec.get("default_expr", {}).get("kind", "N/A")
            print(
                f"    {task.task_id}: template={template}, "
                f"default_expr.kind={default_expr}"
            )


if __name__ == "__main__":
    main()
