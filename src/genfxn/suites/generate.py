"""Pool generation and family-level suite generation."""

import random
import zlib
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

from genfxn.bitops.task import generate_bitops_task
from genfxn.core.models import Task
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.task import generate_intervals_task
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.suites.features import (
    bitops_features,
    fsm_features,
    graph_queries_features,
    intervals_features,
    sequence_dp_features,
    simple_algorithms_features,
    stack_bytecode_features,
    stateful_features,
    stringrules_features,
    temporal_logic_features,
)
from genfxn.suites.quotas import QUOTAS, QuotaSpec
from genfxn.temporal_logic.task import generate_temporal_logic_task


class Candidate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task: Task
    spec_dict: dict[str, Any]
    task_id: str
    features: dict[str, str]


class PoolStats(BaseModel):
    total_sampled: int = 0
    duplicates: int = 0
    errors: int = 0
    candidates: int = 0


_TaskGenerator = Callable[[random.Random], Task]
_FeatureExtractor = Callable[[dict[str, Any]], dict[str, str]]


def _stable_seed(seed: int, family: str, index: int) -> int:
    return zlib.crc32(f"{seed}:{family}:{index}".encode()) & 0xFFFFFFFF


_TASK_GENERATORS: dict[str, _TaskGenerator] = {
    "piecewise": lambda rng: generate_piecewise_task(rng=rng),
    "stateful": lambda rng: generate_stateful_task(rng=rng),
    "simple_algorithms": lambda rng: generate_simple_algorithms_task(rng=rng),
    "stringrules": lambda rng: generate_stringrules_task(rng=rng),
    "stack_bytecode": lambda rng: generate_stack_bytecode_task(rng=rng),
    "fsm": lambda rng: generate_fsm_task(rng=rng),
    "bitops": lambda rng: generate_bitops_task(rng=rng),
    "sequence_dp": lambda rng: generate_sequence_dp_task(rng=rng),
    "intervals": lambda rng: generate_intervals_task(rng=rng),
    "graph_queries": lambda rng: generate_graph_queries_task(rng=rng),
    "temporal_logic": lambda rng: generate_temporal_logic_task(rng=rng),
}

_FEATURE_EXTRACTORS: dict[str, _FeatureExtractor] = {
    "piecewise": lambda _spec: {},
    "stateful": stateful_features,
    "simple_algorithms": simple_algorithms_features,
    "stringrules": stringrules_features,
    "stack_bytecode": stack_bytecode_features,
    "fsm": fsm_features,
    "bitops": bitops_features,
    "sequence_dp": sequence_dp_features,
    "intervals": intervals_features,
    "graph_queries": graph_queries_features,
    "temporal_logic": temporal_logic_features,
}


def _validate_family(family: str) -> None:
    if family not in QUOTAS:
        valid = ", ".join(sorted(QUOTAS))
        raise ValueError(f"Unknown family '{family}'. Valid: {valid}")


def _matches_hard_constraints(
    features: dict[str, str], hard_constraints: dict[str, str]
) -> bool:
    for axis, value in hard_constraints.items():
        if features.get(axis) != value:
            return False
    return True


def generate_pool(
    family: str,
    seed: int = 42,
    pool_size: int = 3000,
) -> tuple[list[Candidate], PoolStats]:
    """Generate a candidate pool for a family."""
    _validate_family(family)
    if pool_size <= 0:
        raise ValueError("pool_size must be > 0")

    generate_task = _TASK_GENERATORS[family]
    extract_features = _FEATURE_EXTRACTORS[family]

    stats = PoolStats()
    seen_ids: set[str] = set()
    candidates: list[Candidate] = []

    for i in range(pool_size):
        stats.total_sampled += 1
        sub_rng = random.Random(_stable_seed(seed, family, i))
        try:
            task = generate_task(sub_rng)
        except Exception:
            stats.errors += 1
            continue

        if task.task_id in seen_ids:
            stats.duplicates += 1
            continue
        seen_ids.add(task.task_id)

        spec_dict = task.spec
        candidates.append(
            Candidate(
                task=task,
                spec_dict=spec_dict,
                task_id=task.task_id,
                features=extract_features(spec_dict),
            )
        )

    stats.candidates = len(candidates)
    return candidates, stats


def generate_suite(
    family: str,
    seed: int = 42,
    pool_size: int = 3000,
    max_retries: int = 3,
) -> list[Task]:
    """Generate a balanced suite for a family."""
    _validate_family(family)
    if pool_size <= 0:
        raise ValueError("pool_size must be > 0")
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    quota = QUOTAS[family]
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        attempt_seed = _stable_seed(seed, family, 800_000 + attempt)
        candidates, _stats = generate_pool(
            family=family,
            seed=attempt_seed,
            pool_size=pool_size,
        )
        filtered = [
            candidate
            for candidate in candidates
            if _matches_hard_constraints(
                candidate.features, quota.hard_constraints
            )
        ]
        if len(filtered) >= quota.total:
            return [candidate.task for candidate in filtered[: quota.total]]
        last_error = (
            f"need {quota.total} tasks, found {len(filtered)} after "
            f"hard-constraint filtering"
        )

    raise ValueError(
        f"Could not generate suite for family '{family}': {last_error}"
    )


def quota_report(
    tasks: list[Task],
    family: str,
) -> list[tuple[str, str, int, int, str]]:
    """Return bucket-level quota report for a generated suite."""
    _validate_family(family)
    quota: QuotaSpec = QUOTAS[family]
    extract_features = _FEATURE_EXTRACTORS[family]
    features = [extract_features(task.spec) for task in tasks]

    report: list[tuple[str, str, int, int, str]] = []
    for bucket in quota.buckets:
        achieved = 0
        for row in features:
            if bucket.condition is not None:
                if any(row.get(k) != v for k, v in bucket.condition.items()):
                    continue
            if row.get(bucket.axis) == bucket.value:
                achieved += 1
        status = "OK" if achieved >= bucket.target else "MISS"
        report.append(
            (bucket.axis, bucket.value, bucket.target, achieved, status)
        )
    return report
