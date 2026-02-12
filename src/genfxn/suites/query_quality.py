"""Query quality guardrails for generated tasks.

This module computes per-task and aggregate quality metrics and applies
base checks plus family-specific semantic checks.
"""

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from genfxn.core.models import Task
from genfxn.core.predicates import eval_predicate
from genfxn.core.string_predicates import eval_string_predicate
from genfxn.core.string_transforms import (
    StringTransformPipeline,
    StringTransformReplace,
)
from genfxn.piecewise.models import PiecewiseSpec
from genfxn.stringrules.models import StringRulesSpec

_MIN_QUERIES = 5
_MIN_DISTINCT_INPUTS = 5
_MIN_TAG_KINDS = 2
_MAX_IDENTITY_RATIO_BY_FAMILY = {
    "piecewise": 0.98,
    "bitops": 0.98,
}
_STRINGRULES_REPLACE_HIT_MIN_RATIO = 0.25


@dataclass(frozen=True)
class QualityCheckResult:
    check_id: str
    passed: bool
    detail: str
    applies: bool = True


@dataclass(frozen=True)
class QueryQualityMetrics:
    query_count: int
    distinct_input_count: int
    distinct_output_count: int
    tag_counts: dict[str, int]
    comparable_identity_count: int
    identity_count: int
    identity_ratio: float | None


@dataclass
class TaskQualityReport:
    task: Task
    metrics: QueryQualityMetrics
    checks: list[QualityCheckResult]

    @property
    def failed_checks(self) -> list[QualityCheckResult]:
        return [
            check
            for check in self.checks
            if check.applies and not check.passed
        ]


@dataclass(frozen=True)
class AggregateQualityMetrics:
    task_count: int
    task_failure_count: int
    replace_old_values_reachable: int
    replace_old_values_hit: int
    replace_hit_ratio: float | None


@dataclass
class AggregateQualityReport:
    family: str
    difficulty: int
    task_reports: list[TaskQualityReport]
    metrics: AggregateQualityMetrics
    checks: list[QualityCheckResult]

    @property
    def failed_checks(self) -> list[QualityCheckResult]:
        return [
            check
            for check in self.checks
            if check.applies and not check.passed
        ]


def _pass(check_id: str, detail: str) -> QualityCheckResult:
    return QualityCheckResult(check_id=check_id, passed=True, detail=detail)


def _fail(check_id: str, detail: str) -> QualityCheckResult:
    return QualityCheckResult(check_id=check_id, passed=False, detail=detail)


def _skip(check_id: str, detail: str) -> QualityCheckResult:
    return QualityCheckResult(
        check_id=check_id,
        passed=True,
        detail=detail,
        applies=False,
    )


def _stable_key(value: Any) -> Any:
    if isinstance(value, dict):
        return (
            "dict",
            tuple(
                sorted(
                    (_stable_key(k), _stable_key(v))
                    for k, v in value.items()
                )
            ),
        )
    if isinstance(value, list):
        return ("list", tuple(_stable_key(item) for item in value))
    if isinstance(value, tuple):
        return ("tuple", tuple(_stable_key(item) for item in value))
    if isinstance(value, set):
        return (
            "set",
            tuple(sorted(_stable_key(item) for item in value)),
        )
    if isinstance(value, frozenset):
        return (
            "frozenset",
            tuple(sorted(_stable_key(item) for item in value)),
        )

    try:
        hash(value)
        return (type(value).__name__, value)
    except TypeError:
        return (type(value).__name__, repr(value))


def _values_equal(left: Any, right: Any) -> bool:
    try:
        return left == right
    except Exception:
        return False


def compute_task_metrics(task: Task) -> QueryQualityMetrics:
    query_count = len(task.queries)
    distinct_inputs = {_stable_key(query.input) for query in task.queries}
    distinct_outputs = {_stable_key(query.output) for query in task.queries}
    tag_counts = Counter(query.tag.value for query in task.queries)

    comparable_pairs = [
        query
        for query in task.queries
        if type(query.input) is type(query.output)
    ]
    comparable_identity_count = len(comparable_pairs)
    identity_count = sum(
        1
        for query in comparable_pairs
        if _values_equal(query.input, query.output)
    )

    identity_ratio: float | None
    if comparable_identity_count == 0:
        identity_ratio = None
    else:
        identity_ratio = identity_count / comparable_identity_count

    return QueryQualityMetrics(
        query_count=query_count,
        distinct_input_count=len(distinct_inputs),
        distinct_output_count=len(distinct_outputs),
        tag_counts=dict(tag_counts),
        comparable_identity_count=comparable_identity_count,
        identity_count=identity_count,
        identity_ratio=identity_ratio,
    )


def _base_checks(
    task: Task, metrics: QueryQualityMetrics
) -> list[QualityCheckResult]:
    checks: list[QualityCheckResult] = []

    if metrics.query_count >= _MIN_QUERIES:
        checks.append(
            _pass(
                "base.query_count_min",
                f"query_count={metrics.query_count} >= {_MIN_QUERIES}",
            )
        )
    else:
        checks.append(
            _fail(
                "base.query_count_min",
                f"query_count={metrics.query_count} < {_MIN_QUERIES}",
            )
        )

    if metrics.distinct_input_count >= _MIN_DISTINCT_INPUTS:
        checks.append(
            _pass(
                "base.distinct_inputs_min",
                "distinct_input_count="
                f"{metrics.distinct_input_count} >= {_MIN_DISTINCT_INPUTS}",
            )
        )
    else:
        checks.append(
            _fail(
                "base.distinct_inputs_min",
                "distinct_input_count="
                f"{metrics.distinct_input_count} < {_MIN_DISTINCT_INPUTS}",
            )
        )

    present_tag_kinds = sum(
        1 for count in metrics.tag_counts.values() if count > 0
    )
    if present_tag_kinds >= _MIN_TAG_KINDS:
        checks.append(
            _pass(
                "base.tag_kinds_min",
                f"tag kinds present={present_tag_kinds} >= "
                f"{_MIN_TAG_KINDS}",
            )
        )
    else:
        checks.append(
            _fail(
                "base.tag_kinds_min",
                f"tag kinds present={present_tag_kinds} < "
                f"{_MIN_TAG_KINDS}",
            )
        )

    max_identity_ratio = _MAX_IDENTITY_RATIO_BY_FAMILY.get(task.family)
    if max_identity_ratio is None:
        checks.append(
            _skip(
                "base.identity_ratio_max",
                "identity ratio cap not configured for this family",
            )
        )
    elif metrics.identity_ratio is None:
        checks.append(
            _skip(
                "base.identity_ratio_max",
                "no same-type input/output pairs to evaluate identity ratio",
            )
        )
    elif metrics.identity_ratio <= max_identity_ratio:
        checks.append(
            _pass(
                "base.identity_ratio_max",
                "identity_ratio="
                f"{metrics.identity_ratio:.3f} <= {max_identity_ratio:.3f}",
            )
        )
    else:
        checks.append(
            _fail(
                "base.identity_ratio_max",
                "identity_ratio="
                f"{metrics.identity_ratio:.3f} > {max_identity_ratio:.3f}",
            )
        )

    return checks


def _piecewise_has_branch_hit(task: Task) -> list[QualityCheckResult]:
    spec = PiecewiseSpec.model_validate(task.spec)
    for query in task.queries:
        if type(query.input) is not int:
            continue
        for branch in spec.branches:
            if eval_predicate(branch.condition, query.input):
                return [
                    _pass(
                        "piecewise.branch_hit",
                        "at least one query hits a non-default branch",
                    )
                ]

    return [
        _fail(
            "piecewise.branch_hit",
            "no query hit any non-default branch",
        )
    ]


def _stateful_non_empty_sequences(task: Task) -> list[QualityCheckResult]:
    has_non_empty = any(
        isinstance(query.input, list) and len(query.input) > 0
        for query in task.queries
    )
    if has_non_empty:
        return [
            _pass(
                "stateful.non_empty_sequence",
                "at least one query includes non-empty sequence input",
            )
        ]
    return [
        _fail(
            "stateful.non_empty_sequence",
            "all query inputs are empty sequences",
        )
    ]


def _simple_algorithms_nontrivial_inputs(
    task: Task,
) -> list[QualityCheckResult]:
    has_len_at_least_two = any(
        isinstance(query.input, list) and len(query.input) >= 2
        for query in task.queries
    )
    if has_len_at_least_two:
        return [
            _pass(
                "simple_algorithms.list_len_ge_2",
                "at least one query has list length >= 2",
            )
        ]
    return [
        _fail(
            "simple_algorithms.list_len_ge_2",
            "no query has list length >= 2",
        )
    ]


def _first_matching_rule_index(spec: StringRulesSpec, s: str) -> int | None:
    for index, rule in enumerate(spec.rules):
        if eval_string_predicate(rule.predicate, s):
            return index
    return None


def _iter_replace_old_values(transform: Any) -> Iterable[str]:
    if isinstance(transform, StringTransformReplace):
        yield transform.old
        return
    if isinstance(transform, StringTransformPipeline):
        for step in transform.steps:
            yield from _iter_replace_old_values(step)


def _stringrules_replace_coverage(task: Task) -> tuple[int, int]:
    spec = StringRulesSpec.model_validate(task.spec)
    applied_inputs: dict[int, list[str]] = {
        i: [] for i in range(len(spec.rules))
    }

    for query in task.queries:
        if not isinstance(query.input, str):
            continue
        match_index = _first_matching_rule_index(spec, query.input)
        if match_index is not None:
            applied_inputs[match_index].append(query.input)

    reachable_old_values = 0
    hit_old_values = 0
    for index, rule in enumerate(spec.rules):
        old_values = list(_iter_replace_old_values(rule.transform))
        if not old_values:
            continue

        inputs = applied_inputs[index]
        if not inputs:
            continue

        for old_value in old_values:
            reachable_old_values += 1
            if any(old_value in candidate for candidate in inputs):
                hit_old_values += 1

    return reachable_old_values, hit_old_values


def _stringrules_replace_hits(task: Task) -> list[QualityCheckResult]:
    if task.difficulty is not None and task.difficulty < 4:
        return [
            _skip(
                "stringrules.replacement_old_hit",
                "replacement-hit check enforced for difficulty >= 4",
            )
        ]

    reachable_old_values, hit_old_values = _stringrules_replace_coverage(task)
    if reachable_old_values == 0:
        return [
            _skip(
                "stringrules.replacement_old_hit",
                "no reachable replace old-values in sampled queries",
            )
        ]

    if hit_old_values == reachable_old_values:
        return [
            _pass(
                "stringrules.replacement_old_hit",
                "all reachable replace old-values were observed in inputs "
                f"({hit_old_values}/{reachable_old_values})",
            )
        ]

    return [
        _fail(
            "stringrules.replacement_old_hit",
            "replace old-values hit ratio was "
            f"{hit_old_values}/{reachable_old_values}",
        )
    ]


def _stack_bytecode_non_empty_inputs(task: Task) -> list[QualityCheckResult]:
    has_non_empty = any(
        isinstance(query.input, list) and len(query.input) > 0
        for query in task.queries
    )
    if has_non_empty:
        return [
            _pass(
                "stack_bytecode.non_empty_input",
                "at least one query includes non-empty VM input",
            )
        ]
    return [
        _fail(
            "stack_bytecode.non_empty_input",
            "all VM query inputs are empty",
        )
    ]


def _fsm_non_empty_inputs(task: Task) -> list[QualityCheckResult]:
    has_non_empty = any(
        isinstance(query.input, list) and len(query.input) > 0
        for query in task.queries
    )
    if has_non_empty:
        return [
            _pass(
                "fsm.non_empty_input",
                "at least one query includes non-empty symbol sequence",
            )
        ]
    return [
        _fail(
            "fsm.non_empty_input",
            "all FSM query inputs are empty",
        )
    ]


def _bitops_non_zero_input(task: Task) -> list[QualityCheckResult]:
    has_non_zero = any(
        type(query.input) is int and query.input != 0
        for query in task.queries
    )
    if has_non_zero:
        return [
            _pass(
                "bitops.non_zero_input",
                "at least one query uses non-zero input",
            )
        ]
    return [
        _fail(
            "bitops.non_zero_input",
            "all bitops query inputs are zero",
        )
    ]


def _sequence_dp_non_empty_alignment(task: Task) -> list[QualityCheckResult]:
    has_non_empty = any(
        isinstance(query.input, dict)
        and (
            len(query.input.get("a", [])) > 0
            or len(query.input.get("b", [])) > 0
        )
        for query in task.queries
    )
    if has_non_empty:
        return [
            _pass(
                "sequence_dp.non_empty_alignment",
                "at least one query has non-empty alignment input",
            )
        ]
    return [
        _fail(
            "sequence_dp.non_empty_alignment",
            "all sequence_dp query alignments are empty",
        )
    ]


def _intervals_non_empty_interval_set(task: Task) -> list[QualityCheckResult]:
    has_non_empty = any(
        isinstance(query.input, list) and len(query.input) > 0
        for query in task.queries
    )
    if has_non_empty:
        return [
            _pass(
                "intervals.non_empty_interval_set",
                "at least one query provides non-empty interval set",
            )
        ]
    return [
        _fail(
            "intervals.non_empty_interval_set",
            "all interval query inputs are empty",
        )
    ]


def _graph_queries_distinct_endpoints(task: Task) -> list[QualityCheckResult]:
    has_distinct_endpoints = any(
        isinstance(query.input, dict)
        and query.input.get("src") != query.input.get("dst")
        for query in task.queries
    )
    if has_distinct_endpoints:
        return [
            _pass(
                "graph_queries.distinct_endpoints",
                "at least one query has src != dst",
            )
        ]
    return [
        _fail(
            "graph_queries.distinct_endpoints",
            "all graph queries use src == dst",
        )
    ]


def _temporal_logic_nontrivial_trace(task: Task) -> list[QualityCheckResult]:
    has_nontrivial = any(
        isinstance(query.input, list) and len(query.input) >= 2
        for query in task.queries
    )
    if has_nontrivial:
        return [
            _pass(
                "temporal_logic.nontrivial_trace",
                "at least one query has trace length >= 2",
            )
        ]
    return [
        _fail(
            "temporal_logic.nontrivial_trace",
            "all temporal traces are length < 2",
        )
    ]


FamilyHook = Callable[[Task], list[QualityCheckResult]]

QUALITY_HOOKS: dict[str, FamilyHook] = {
    "piecewise": _piecewise_has_branch_hit,
    "stateful": _stateful_non_empty_sequences,
    "simple_algorithms": _simple_algorithms_nontrivial_inputs,
    "stringrules": _stringrules_replace_hits,
    "stack_bytecode": _stack_bytecode_non_empty_inputs,
    "fsm": _fsm_non_empty_inputs,
    "bitops": _bitops_non_zero_input,
    "sequence_dp": _sequence_dp_non_empty_alignment,
    "intervals": _intervals_non_empty_interval_set,
    "graph_queries": _graph_queries_distinct_endpoints,
    "temporal_logic": _temporal_logic_nontrivial_trace,
}


def evaluate_task_quality(task: Task) -> TaskQualityReport:
    metrics = compute_task_metrics(task)
    checks = _base_checks(task, metrics)

    hook = QUALITY_HOOKS.get(task.family)
    if hook is None:
        checks.append(
            _skip(
                "family.hook",
                f"no family hook registered for family '{task.family}'",
            )
        )
    else:
        checks.extend(hook(task))

    return TaskQualityReport(task=task, metrics=metrics, checks=checks)


def evaluate_aggregate_quality(
    family: str,
    difficulty: int,
    tasks: list[Task],
) -> AggregateQualityReport:
    task_reports = [evaluate_task_quality(task) for task in tasks]
    task_failure_count = sum(
        1 for report in task_reports if report.failed_checks
    )

    total_reachable_old_values = 0
    total_hit_old_values = 0
    if family == "stringrules" and difficulty >= 4:
        for task in tasks:
            reachable, hit = _stringrules_replace_coverage(task)
            total_reachable_old_values += reachable
            total_hit_old_values += hit

    replace_hit_ratio: float | None
    if total_reachable_old_values == 0:
        replace_hit_ratio = None
    else:
        replace_hit_ratio = (
            total_hit_old_values / total_reachable_old_values
        )

    metrics = AggregateQualityMetrics(
        task_count=len(tasks),
        task_failure_count=task_failure_count,
        replace_old_values_reachable=total_reachable_old_values,
        replace_old_values_hit=total_hit_old_values,
        replace_hit_ratio=replace_hit_ratio,
    )

    checks: list[QualityCheckResult] = []
    if metrics.task_count > 0:
        checks.append(
            _pass(
                "aggregate.task_count_nonzero",
                f"task_count={metrics.task_count}",
            )
        )
    else:
        checks.append(_fail("aggregate.task_count_nonzero", "no tasks"))

    if metrics.task_failure_count == 0:
        checks.append(
            _pass(
                "aggregate.no_task_failures",
                "all sampled tasks passed per-task quality checks",
            )
        )
    else:
        checks.append(
            _fail(
                "aggregate.no_task_failures",
                f"{metrics.task_failure_count} tasks failed quality checks",
            )
        )

    if family == "stringrules" and difficulty >= 4:
        if replace_hit_ratio is None:
            checks.append(
                _skip(
                    "aggregate.stringrules_replace_hit_ratio",
                    "no reachable replace old-values across sampled tasks",
                )
            )
        elif replace_hit_ratio >= _STRINGRULES_REPLACE_HIT_MIN_RATIO:
            checks.append(
                _pass(
                    "aggregate.stringrules_replace_hit_ratio",
                    "replace hit ratio "
                    f"{replace_hit_ratio:.3f} >= "
                    f"{_STRINGRULES_REPLACE_HIT_MIN_RATIO:.3f}",
                )
            )
        else:
            checks.append(
                _fail(
                    "aggregate.stringrules_replace_hit_ratio",
                    "replace hit ratio "
                    f"{replace_hit_ratio:.3f} < "
                    f"{_STRINGRULES_REPLACE_HIT_MIN_RATIO:.3f}",
                )
            )

    return AggregateQualityReport(
        family=family,
        difficulty=difficulty,
        task_reports=task_reports,
        metrics=metrics,
        checks=checks,
    )


def format_aggregate_failures(
    report: AggregateQualityReport,
    *,
    max_task_failures: int = 8,
) -> str:
    lines = [
        f"{report.family} D{report.difficulty} failed quality checks",
        f"aggregate metrics: {report.metrics}",
    ]

    for check in report.failed_checks:
        lines.append(
            f"aggregate check failed [{check.check_id}]: {check.detail}"
        )

    shown = 0
    for task_report in report.task_reports:
        if not task_report.failed_checks:
            continue
        lines.append(f"task {task_report.task.task_id} failures:")
        for check in task_report.failed_checks:
            lines.append(f"  - [{check.check_id}] {check.detail}")
        shown += 1
        if shown >= max_task_failures:
            break

    omitted = report.metrics.task_failure_count - shown
    if omitted > 0:
        lines.append(f"... {omitted} additional failing tasks omitted")

    return "\n".join(lines)
