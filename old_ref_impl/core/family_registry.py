from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

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
from genfxn.temporal_logic.task import generate_temporal_logic_task

TaskGenerator = Callable[[random.Random, Any | None], Task]


FAMILY_ORDER: tuple[str, ...] = (
    "piecewise",
    "stateful",
    "simple_algorithms",
    "stringrules",
    "bitops",
    "sequence_dp",
    "intervals",
    "graph_queries",
    "temporal_logic",
    "stack_bytecode",
    "fsm",
)

_TASK_GENERATORS: dict[str, TaskGenerator] = {
    "piecewise": lambda rng, axes: generate_piecewise_task(rng=rng, axes=axes),
    "stateful": lambda rng, axes: generate_stateful_task(rng=rng, axes=axes),
    "simple_algorithms": lambda rng, axes: generate_simple_algorithms_task(
        rng=rng,
        axes=axes,
    ),
    "stringrules": lambda rng, axes: generate_stringrules_task(
        rng=rng,
        axes=axes,
    ),
    "bitops": lambda rng, axes: generate_bitops_task(rng=rng, axes=axes),
    "sequence_dp": lambda rng, axes: generate_sequence_dp_task(
        rng=rng,
        axes=axes,
    ),
    "intervals": lambda rng, axes: generate_intervals_task(rng=rng, axes=axes),
    "graph_queries": lambda rng, axes: generate_graph_queries_task(
        rng=rng,
        axes=axes,
    ),
    "temporal_logic": lambda rng, axes: generate_temporal_logic_task(
        rng=rng,
        axes=axes,
    ),
    "stack_bytecode": lambda rng, axes: generate_stack_bytecode_task(
        rng=rng,
        axes=axes,
    ),
    "fsm": lambda rng, axes: generate_fsm_task(rng=rng, axes=axes),
}


KNOWN_FAMILIES: frozenset[str] = frozenset(FAMILY_ORDER)


def parse_family_selector(families: str) -> list[str]:
    """Parse selectors, deduplicate repeats, and keep FAMILY_ORDER order."""
    if families == "all":
        return list(FAMILY_ORDER)

    selected = [
        family.strip() for family in families.split(",") if family.strip()
    ]
    if not selected:
        raise ValueError("families must not be empty")

    invalid = [family for family in selected if family not in KNOWN_FAMILIES]
    if invalid:
        valid = ", ".join(FAMILY_ORDER)
        bad = ", ".join(invalid)
        raise ValueError(f"Invalid families: {bad}. Valid options: {valid}")

    selected_set = set(selected)
    return [family for family in FAMILY_ORDER if family in selected_set]


def generate_task_for_family(
    family: str,
    *,
    rng: random.Random,
    axes: Any | None = None,
) -> Task:
    generator = _TASK_GENERATORS.get(family)
    if generator is None:
        valid = ", ".join(FAMILY_ORDER)
        raise ValueError(f"Unknown family '{family}'. Valid options: {valid}")
    return generator(rng, axes)
