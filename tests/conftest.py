from __future__ import annotations

from pathlib import Path

import pytest

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
