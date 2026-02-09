import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import srsly

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "generate_balanced_suites.py"
)


def _load_script_module(script: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load script module from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT_MODULE = _load_script_module(
    _SCRIPT, "tests.generate_balanced_suites_script_module"
)
generate_balanced_suites_main = cast(
    Callable[..., None], getattr(_SCRIPT_MODULE, "main")
)


class _FakeTask:
    def __init__(self, task_id: str) -> None:
        self._task_id = task_id

    def model_dump(self, mode: str = "json") -> dict[str, str]:  # noqa: ARG002
        return {"task_id": self._task_id}


def test_main_parses_filters_and_writes_output(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, int, int, int]] = []

    def _fake_generate_suite(
        family: str, difficulty: int, seed: int, pool_size: int
    ) -> list[_FakeTask]:
        calls.append((family, difficulty, seed, pool_size))
        return [_FakeTask(f"{family}_{difficulty}")]

    def _fake_quota_report(
        tasks: list[_FakeTask],
        family: str,  # noqa: ARG001
        difficulty: int,  # noqa: ARG001
    ) -> list[tuple[str, str, int, int, str]]:
        assert tasks
        return [("axis", "value", 1, 1, "OK")]

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

    generate_balanced_suites_main(
        output_dir=tmp_path,
        seed=7,
        pool_size=11,
        families="stateful,stringrules",
        difficulties="3,5",
    )

    assert calls == [
        ("stateful", 3, 7, 11),
        ("stateful", 5, 7, 11),
        ("stringrules", 3, 7, 11),
        ("stringrules", 5, 7, 11),
    ]

    for family in ("stateful", "stringrules"):
        for difficulty in (3, 5):
            output = tmp_path / family / f"level_{difficulty}" / "all.jsonl"
            records = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
            assert records == [{"task_id": f"{family}_{difficulty}"}]
