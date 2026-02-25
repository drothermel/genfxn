from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path

import pytest

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

_FAMILIES = frozenset(
    {
        "bitops",
        "fsm",
        "graph_queries",
        "intervals",
        "piecewise",
        "sequence_dp",
        "simple_algorithms",
        "stack_bytecode",
        "stateful",
        "stringrules",
        "temporal_logic",
    }
)


def _full_family_marker_for_item(item: pytest.Item) -> str | None:
    filename = Path(item.path).name
    family: str | None = None
    if filename.startswith("test_validate_") and filename.endswith(".py"):
        family = filename[len("test_validate_") : -len(".py")]
    elif filename.startswith("test_") and filename.endswith(
        "_runtime_parity.py"
    ):
        family = filename[len("test_") : -len("_runtime_parity.py")]
    if family in _FAMILIES:
        return f"full_{family}"
    return None


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--verification-level",
        action="store",
        default="standard",
        choices=("fast", "standard", "full"),
        help=(
            "Select test verification level: "
            "fast (skip slow+full), "
            "standard (skip full), "
            "full (run all)."
        ),
    )


def pytest_itemcollected(item: pytest.Item) -> None:
    if "full" not in item.keywords:
        return
    family_marker = _full_family_marker_for_item(item)
    if family_marker is None:
        return
    item.add_marker(getattr(pytest.mark, family_marker))


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    level = config.getoption("--verification-level")

    if level == "full":
        return

    skip_full = pytest.mark.skip(reason="requires --verification-level=full")
    skip_slow = pytest.mark.skip(reason="skipped in fast verification level")

    for item in items:
        if "full" in item.keywords:
            item.add_marker(skip_full)
            continue
        if level == "fast" and "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def task_factories() -> tuple[Callable[[], Task], ...]:
    return (
        lambda: generate_piecewise_task(rng=random.Random(1)),
        lambda: generate_stateful_task(rng=random.Random(1)),
        lambda: generate_simple_algorithms_task(rng=random.Random(1)),
        lambda: generate_stringrules_task(rng=random.Random(1)),
        lambda: generate_stack_bytecode_task(rng=random.Random(1)),
        lambda: generate_fsm_task(rng=random.Random(1)),
        lambda: generate_bitops_task(rng=random.Random(1)),
        lambda: generate_sequence_dp_task(rng=random.Random(1)),
        lambda: generate_intervals_task(rng=random.Random(1)),
        lambda: generate_graph_queries_task(rng=random.Random(1)),
        lambda: generate_temporal_logic_task(rng=random.Random(1)),
    )
