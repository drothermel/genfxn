import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "analyze_difficulty.py"
)
_SCRIPT_NS = runpy.run_path(str(_SCRIPT))
analyze_family = cast(Callable[[str], Any], _SCRIPT_NS["analyze_family"])


def test_stateful_reports_difficulty_5_as_achievable() -> None:
    analysis = analyze_family("stateful")
    assert 5 in analysis.achievable_difficulties


def test_stringrules_reports_difficulty_5_as_achievable() -> None:
    analysis = analyze_family("stringrules")
    assert 5 in analysis.achievable_difficulties


def test_simple_algorithms_reports_valid_difficulties() -> None:
    analysis = analyze_family("simple_algorithms")
    assert analysis.achievable_difficulties == [2, 3, 4, 5]
