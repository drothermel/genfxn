import random

import pytest

from genfxn.core.family_registry import (
    FAMILY_ORDER,
    generate_task_for_family,
    parse_family_selector,
)


def test_parse_family_selector_all_returns_canonical_order() -> None:
    assert parse_family_selector("all") == list(FAMILY_ORDER)


def test_parse_family_selector_empty_selector_raises_value_error() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        parse_family_selector("")


def test_parse_family_selector_normalizes_to_canonical_order() -> None:
    selected = parse_family_selector("fsm,piecewise,fsm")
    assert selected == ["piecewise", "fsm"]


def test_parse_family_selector_rejects_unknown_family() -> None:
    with pytest.raises(ValueError, match="Invalid families"):
        parse_family_selector("piecewise,unknown")


def test_generate_task_for_family_supported_families() -> None:
    for family in FAMILY_ORDER:
        task = generate_task_for_family(family, rng=random.Random(7), axes=None)
        assert task.family == family
