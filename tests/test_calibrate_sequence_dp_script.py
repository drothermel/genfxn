import importlib.util
import json
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from click.exceptions import Exit

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "calibrate_sequence_dp.py"
)


def _load_script_module(script: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load script module from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT_MODULE = _load_script_module(
    _SCRIPT, "tests.calibrate_sequence_dp_script_module"
)
calibrate_sequence_dp_main = cast(
    Callable[..., None], getattr(_SCRIPT_MODULE, "main")
)


class _FakeAxes:
    def __init__(self, difficulty: int) -> None:
        self.difficulty = difficulty


class _FakeGeneratedTask:
    def __init__(self, difficulty: int) -> None:
        self.difficulty = difficulty


class _FakeSuiteTask:
    def __init__(self) -> None:
        self.spec: dict[str, Any] = {}


def test_main_writes_report_when_strict_checks_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_get_difficulty_axes(
        family: str, difficulty: int, rng: object
    ) -> _FakeAxes:
        assert family == "sequence_dp"
        assert rng is not None
        return _FakeAxes(difficulty)

    def _fake_generate_sequence_dp_task(
        axes: _FakeAxes, rng: object
    ) -> _FakeGeneratedTask:
        assert rng is not None
        return _FakeGeneratedTask(axes.difficulty)

    def _fake_generate_suite(
        family: str,
        difficulty: int,
        seed: int,
        pool_size: int,
    ) -> list[_FakeSuiteTask]:
        assert family == "sequence_dp"
        assert difficulty in {1, 2, 3, 4, 5}
        assert seed > 0
        assert pool_size > 0
        return [_FakeSuiteTask() for _ in range(50)]

    def _fake_quota_report(
        tasks: list[_FakeSuiteTask],
        family: str,
        difficulty: int,
    ) -> list[tuple[str, str, int, int, str]]:
        assert tasks
        assert family == "sequence_dp"
        assert difficulty in {1, 2, 3, 4, 5}
        return [("axis", "value", 1, 1, "OK")]

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "get_difficulty_axes",
        _fake_get_difficulty_axes,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_sequence_dp_task",
        _fake_generate_sequence_dp_task,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_suite",
        _fake_generate_suite,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "quota_report",
        _fake_quota_report,
    )

    output = tmp_path / "sequence_dp_calibration.json"
    calibrate_sequence_dp_main(
        output=output,
        samples=5,
        seed=7,
        pool_size=11,
        strict=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["family"] == "sequence_dp"
    assert report["strict"]["passed"] is True
    assert report["reachability"]["D3"]["exact"] == 1.0
    assert report["reachability"]["D5"]["within_one"] == 1.0


def test_main_raises_exit_when_strict_checks_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_get_difficulty_axes(
        family: str, difficulty: int, rng: object
    ) -> _FakeAxes:
        assert family == "sequence_dp"
        assert rng is not None
        return _FakeAxes(difficulty)

    def _fake_generate_sequence_dp_task(
        axes: _FakeAxes, rng: object
    ) -> _FakeGeneratedTask:
        assert rng is not None
        return _FakeGeneratedTask(axes.difficulty)

    def _fake_generate_suite(
        family: str,
        difficulty: int,
        seed: int,
        pool_size: int,
    ) -> list[_FakeSuiteTask]:
        assert family == "sequence_dp"
        assert difficulty in {1, 2, 3, 4, 5}
        assert seed > 0
        assert pool_size > 0
        return [_FakeSuiteTask() for _ in range(50)]

    def _fake_quota_report(
        tasks: list[_FakeSuiteTask],
        family: str,
        difficulty: int,
    ) -> list[tuple[str, str, int, int, str]]:
        assert tasks
        assert family == "sequence_dp"
        assert difficulty in {1, 2, 3, 4, 5}
        return [("axis", "value", 1, 0, "UNDER")]

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "get_difficulty_axes",
        _fake_get_difficulty_axes,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_sequence_dp_task",
        _fake_generate_sequence_dp_task,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_suite",
        _fake_generate_suite,
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "quota_report",
        _fake_quota_report,
    )

    output = tmp_path / "sequence_dp_calibration.json"
    with pytest.raises(Exit) as exc_info:
        calibrate_sequence_dp_main(
            output=output,
            samples=5,
            seed=7,
            pool_size=11,
            strict=True,
        )
    assert exc_info.value.exit_code == 1

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["strict"]["passed"] is False
    assert report["strict"]["failures"]
