"""Shared family-selection parsing helpers for suite scripts."""

from __future__ import annotations

import typer

from genfxn.suites.quotas import QUOTAS


def parse_families(families: str) -> list[str]:
    """Parse family selectors and preserve QUOTAS insertion order for 'all'."""
    if families == "all":
        return list(QUOTAS.keys())

    family_list = [
        family.strip() for family in families.split(",") if family.strip()
    ]
    if not family_list:
        raise typer.BadParameter("families must not be empty")

    invalid = [family for family in family_list if family not in QUOTAS]
    if invalid:
        invalid_str = ", ".join(invalid)
        valid = ", ".join(list(QUOTAS.keys()))
        raise typer.BadParameter(
            f"Invalid families: {invalid_str}. Valid options: {valid}"
        )

    # Deduplicate while preserving order
    return list(dict.fromkeys(family_list))
