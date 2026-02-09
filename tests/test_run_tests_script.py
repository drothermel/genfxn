import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from helpers import load_script_module

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_tests.py"


_SCRIPT_MODULE = load_script_module(_SCRIPT, "tests.run_tests_script_module")
parse_duration_seconds = cast(
    Callable[[str], float | None],
    _SCRIPT_MODULE._parse_duration_seconds,
)
run_tests_main = cast(Callable[[], int], _SCRIPT_MODULE.main)
script_subprocess = cast(ModuleType, _SCRIPT_MODULE.subprocess)


def test_parse_duration_seconds_uses_last_match() -> None:
    assert parse_duration_seconds("in 0.20s\nin 1.23s") == 1.23
    assert parse_duration_seconds("no duration here") is None


def test_main_enforces_runtime_budget(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_run(  # noqa: ARG001
        cmd: list[str],
        capture_output: bool,
        text: bool,
    ):
        captured["cmd"] = cmd

        class _Proc:
            returncode = 0
            stdout = "== 10 passed in 2.50s =="
            stderr = ""

        return _Proc()

    monkeypatch.setattr(
        script_subprocess,
        "run",
        _fake_run,
    )
    monkeypatch.setattr(_SCRIPT_MODULE, "_has_xdist", lambda: False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_tests.py",
            "--tier",
            "fast",
            "--enforce-budget",
            "--budget-fast",
            "1.0",
        ],
    )

    assert run_tests_main() == 2
    assert "-n" not in captured["cmd"]


def test_main_adds_xdist_workers_when_available(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def _fake_run(  # noqa: ARG001
        cmd: list[str],
        capture_output: bool,
        text: bool,
    ):
        captured["cmd"] = cmd

        class _Proc:
            returncode = 0
            stdout = "== 10 passed in 0.10s =="
            stderr = ""

        return _Proc()

    monkeypatch.setattr(
        script_subprocess,
        "run",
        _fake_run,
    )
    monkeypatch.setattr(_SCRIPT_MODULE, "_has_xdist", lambda: True)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_tests.py", "--tier", "fast", "--workers", "3"],
    )

    assert run_tests_main() == 0
    assert "-n" in captured["cmd"]
    n_idx = captured["cmd"].index("-n")
    assert captured["cmd"][n_idx + 1] == "3"
