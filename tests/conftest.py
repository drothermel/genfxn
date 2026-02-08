from __future__ import annotations

import pytest


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
