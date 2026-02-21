"""Query-quality checks for generated suites."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from genfxn.core.models import Task


class QualityCheckResult(BaseModel):
    check_id: str
    passed: bool
    detail: str
    skipped: bool = False


class QueryQualityMetrics(BaseModel):
    n_queries: int
    n_distinct_inputs: int
    n_distinct_tags: int
    duplicate_inputs: int


class TaskQualityReport(BaseModel):
    task: Task
    metrics: QueryQualityMetrics
    checks: list[QualityCheckResult]

    @property
    def failed_checks(self) -> list[QualityCheckResult]:
        return [
            check
            for check in self.checks
            if not check.passed and not check.skipped
        ]


class AggregateQualityMetrics(BaseModel):
    n_tasks: int
    avg_queries_per_task: float
    avg_distinct_inputs: float
    pct_tasks_with_failures: float


class AggregateQualityReport(BaseModel):
    family: str
    task_reports: list[TaskQualityReport]
    metrics: AggregateQualityMetrics
    checks: list[QualityCheckResult]

    @property
    def failed_checks(self) -> list[QualityCheckResult]:
        return [
            check
            for check in self.checks
            if not check.passed and not check.skipped
        ]


def _pass(check_id: str, detail: str) -> QualityCheckResult:
    return QualityCheckResult(check_id=check_id, passed=True, detail=detail)


def _fail(check_id: str, detail: str) -> QualityCheckResult:
    return QualityCheckResult(check_id=check_id, passed=False, detail=detail)


def compute_task_metrics(task: Task) -> QueryQualityMetrics:
    inputs = [repr(query.input) for query in task.queries]
    tags = [query.tag.value for query in task.queries]
    counts = Counter(inputs)
    duplicate_inputs = sum(count - 1 for count in counts.values() if count > 1)
    return QueryQualityMetrics(
        n_queries=len(task.queries),
        n_distinct_inputs=len(set(inputs)),
        n_distinct_tags=len(set(tags)),
        duplicate_inputs=duplicate_inputs,
    )


def evaluate_task_quality(task: Task) -> TaskQualityReport:
    metrics = compute_task_metrics(task)
    checks: list[QualityCheckResult] = []

    if metrics.n_queries >= 8:
        checks.append(_pass("query_count_min", f"{metrics.n_queries} queries"))
    else:
        checks.append(
            _fail("query_count_min", f"{metrics.n_queries} queries (< 8)")
        )

    if metrics.n_distinct_inputs >= max(1, metrics.n_queries // 2):
        checks.append(
            _pass(
                "input_diversity_min",
                f"{metrics.n_distinct_inputs} distinct inputs",
            )
        )
    else:
        checks.append(
            _fail(
                "input_diversity_min",
                f"{metrics.n_distinct_inputs} distinct inputs is too low",
            )
        )

    if metrics.n_distinct_tags >= 2:
        checks.append(
            _pass("tag_coverage_min", f"{metrics.n_distinct_tags} tags")
        )
    else:
        checks.append(_fail("tag_coverage_min", "only one query tag present"))

    return TaskQualityReport(task=task, metrics=metrics, checks=checks)


def evaluate_aggregate_quality(
    family: str,
    tasks: list[Task],
) -> AggregateQualityReport:
    task_reports = [evaluate_task_quality(task) for task in tasks]
    n_tasks = len(task_reports)
    if n_tasks == 0:
        metrics = AggregateQualityMetrics(
            n_tasks=0,
            avg_queries_per_task=0.0,
            avg_distinct_inputs=0.0,
            pct_tasks_with_failures=0.0,
        )
        checks = [_fail("non_empty_suite", "suite contains no tasks")]
        return AggregateQualityReport(
            family=family,
            task_reports=task_reports,
            metrics=metrics,
            checks=checks,
        )

    avg_queries = sum(r.metrics.n_queries for r in task_reports) / n_tasks
    avg_distinct_inputs = (
        sum(r.metrics.n_distinct_inputs for r in task_reports) / n_tasks
    )
    failed_tasks = sum(1 for r in task_reports if r.failed_checks)
    pct_failed = failed_tasks / n_tasks

    metrics = AggregateQualityMetrics(
        n_tasks=n_tasks,
        avg_queries_per_task=avg_queries,
        avg_distinct_inputs=avg_distinct_inputs,
        pct_tasks_with_failures=pct_failed,
    )

    checks: list[QualityCheckResult] = []
    if avg_queries >= 10:
        checks.append(_pass("avg_query_count_min", f"avg={avg_queries:.2f}"))
    else:
        checks.append(
            _fail("avg_query_count_min", f"avg={avg_queries:.2f} (< 10)")
        )

    if pct_failed <= 0.1:
        checks.append(
            _pass("task_failure_rate_max", f"failure rate={pct_failed:.1%}")
        )
    else:
        checks.append(
            _fail("task_failure_rate_max", f"failure rate={pct_failed:.1%}")
        )

    return AggregateQualityReport(
        family=family,
        task_reports=task_reports,
        metrics=metrics,
        checks=checks,
    )


def enforce_aggregate_quality(report: AggregateQualityReport) -> None:
    failed = report.failed_checks
    if not failed:
        return
    details = "; ".join(f"{check.check_id}: {check.detail}" for check in failed)
    raise ValueError(f"{report.family} suite failed quality checks: {details}")
