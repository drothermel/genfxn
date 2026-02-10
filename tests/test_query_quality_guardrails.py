import random

from genfxn.bitops.task import generate_bitops_task
from genfxn.core.models import Query, QueryTag, Task
from genfxn.core.presets import get_difficulty_axes, get_valid_difficulties
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.task import generate_intervals_task
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.suites.query_quality import (
    evaluate_aggregate_quality,
    evaluate_task_quality,
    format_aggregate_failures,
)
from genfxn.temporal_logic.task import generate_temporal_logic_task

_GENERATORS = {
    "piecewise": generate_piecewise_task,
    "stateful": generate_stateful_task,
    "simple_algorithms": generate_simple_algorithms_task,
    "stringrules": generate_stringrules_task,
    "stack_bytecode": generate_stack_bytecode_task,
    "fsm": generate_fsm_task,
    "bitops": generate_bitops_task,
    "sequence_dp": generate_sequence_dp_task,
    "intervals": generate_intervals_task,
    "graph_queries": generate_graph_queries_task,
    "temporal_logic": generate_temporal_logic_task,
}


def _sample_tasks(
    family: str,
    difficulty: int,
    *,
    n_tasks: int,
    seed: int,
) -> list[Task]:
    generator = _GENERATORS[family]
    tasks: list[Task] = []

    for offset in range(n_tasks):
        rng = random.Random(seed + offset)
        axes = get_difficulty_axes(family, difficulty, rng=rng)
        task = generator(axes=axes, rng=rng)
        tasks.append(task)

    return tasks


def _stringrules_task_for_replace_coverage(
    *,
    includes_old: bool,
) -> Task:
    base = "xabcd" if includes_old else "xwxyz"
    spec = {
        "rules": [
            {
                "predicate": {"kind": "starts_with", "prefix": "x"},
                "transform": {"kind": "replace", "old": "ab", "new": "Q"},
            }
        ],
        "default_transform": {"kind": "identity"},
    }
    inputs = [base, base + "1", base + "2", base + "3", base + "4"]
    outputs = [
        value.replace("ab", "Q") if includes_old else value for value in inputs
    ]

    queries = [
        Query(input=inputs[0], output=outputs[0], tag=QueryTag.COVERAGE),
        Query(input=inputs[1], output=outputs[1], tag=QueryTag.TYPICAL),
        Query(input=inputs[2], output=outputs[2], tag=QueryTag.BOUNDARY),
        Query(input=inputs[3], output=outputs[3], tag=QueryTag.ADVERSARIAL),
        Query(input=inputs[4], output=outputs[4], tag=QueryTag.TYPICAL),
    ]

    return Task(
        task_id=f"test_replace_{'hit' if includes_old else 'miss'}",
        family="stringrules",
        spec=spec,
        code="",
        queries=queries,
        trace=None,
        axes={},
        difficulty=4,
        description="test task",
    )


def test_stringrules_replace_hook_detects_missing_old_substrings() -> None:
    task = _stringrules_task_for_replace_coverage(includes_old=False)
    report = evaluate_task_quality(task)

    failed_ids = {check.check_id for check in report.failed_checks}
    assert "stringrules.replacement_old_hit" in failed_ids


def test_stringrules_replace_hook_passes_when_old_is_hit() -> None:
    task = _stringrules_task_for_replace_coverage(includes_old=True)
    report = evaluate_task_quality(task)

    failed_ids = {check.check_id for check in report.failed_checks}
    assert "stringrules.replacement_old_hit" not in failed_ids


def test_query_quality_guardrails_all_families_all_difficulties() -> None:
    failures: list[str] = []

    for family in _GENERATORS:
        for difficulty in get_valid_difficulties(family):
            tasks = _sample_tasks(
                family,
                difficulty,
                n_tasks=4,
                seed=20260210 + difficulty,
            )
            aggregate = evaluate_aggregate_quality(family, difficulty, tasks)
            if aggregate.failed_checks:
                failures.append(format_aggregate_failures(aggregate))

    assert not failures, "\n\n".join(failures)
