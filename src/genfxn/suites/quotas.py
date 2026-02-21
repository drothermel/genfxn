"""Quota table definitions for family-level suite generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Bucket:
    axis: str
    value: str
    target: int
    condition: dict[str, str] | None = None


@dataclass(frozen=True)
class QuotaSpec:
    hard_constraints: dict[str, str]
    buckets: list[Bucket]
    total: int = 50


def _empty_quota(total: int = 50) -> QuotaSpec:
    return QuotaSpec(hard_constraints={}, buckets=[], total=total)


QUOTAS: dict[str, QuotaSpec] = {
    "piecewise": _empty_quota(),
    "stateful": _empty_quota(),
    "simple_algorithms": _empty_quota(),
    "stringrules": _empty_quota(),
    "stack_bytecode": _empty_quota(),
    "fsm": _empty_quota(),
    "bitops": _empty_quota(),
    "sequence_dp": _empty_quota(),
    "intervals": _empty_quota(),
    "graph_queries": _empty_quota(),
    "temporal_logic": _empty_quota(),
}
