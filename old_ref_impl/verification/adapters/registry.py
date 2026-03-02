from __future__ import annotations

from genfxn.core.family_registry import FAMILY_ORDER
from genfxn.verification.adapters.base import VerificationFamilyAdapter
from genfxn.verification.adapters.families import ALL_ADAPTERS

_ADAPTERS: dict[str, VerificationFamilyAdapter] = {
    adapter.family: adapter for adapter in ALL_ADAPTERS
}


missing_families = sorted(set(FAMILY_ORDER) - set(_ADAPTERS))
extra_families = sorted(set(_ADAPTERS) - set(FAMILY_ORDER))
if missing_families or extra_families:
    raise RuntimeError(
        "Verification adapter registry mismatch: "
        f"missing={missing_families} extra={extra_families}"
    )


def get_adapter(family: str) -> VerificationFamilyAdapter:
    adapter = _ADAPTERS.get(family)
    if adapter is None:
        raise ValueError(f"Unknown family '{family}'")
    return adapter


def get_registered_families() -> tuple[str, ...]:
    return tuple(family for family in FAMILY_ORDER if family in _ADAPTERS)
