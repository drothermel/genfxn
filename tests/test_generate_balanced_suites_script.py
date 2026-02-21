from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import srsly
from helpers import load_script_module
from typer import Exit

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "generate_balanced_suites.py"
)

_SCRIPT_MODULE = load_script_module(
    _SCRIPT, "tests.generate_balanced_suites_script_module"
)
generate_balanced_suites_main = cast(Callable[..., None], _SCRIPT_MODULE.main)


class _FakeTask:
    def __init__(self, task_id: str) -> None:
        self._task_id = task_id

    def model_dump(self, mode: str = "json") -> dict[str, str]:  # noqa: ARG002
        return {"task_id": self._task_id}


def test_main_parses_filters_and_writes_output(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, int, int]] = []
    checked: list[int] = []

    def _fake_generate_suite(
        family: str, seed: int, pool_size: int
    ) -> list[_FakeTask]:
        calls.append((family, seed, pool_size))
        return [_FakeTask(family)]

    def _fake_quota_report(
        tasks: list[_FakeTask],
        family: str,  # noqa: ARG001
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
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        lambda tasks: checked.append(len(tasks)),
    )

    generate_balanced_suites_main(
        output_dir=tmp_path,
        seed=7,
        pool_size=11,
        families="stateful,stringrules",
        skip_generated_style_checks=False,
    )

    assert calls == [
        ("stateful", 7, 11),
        ("stringrules", 7, 11),
    ]
    assert checked == [1, 1]

    for family in ("stateful", "stringrules"):
        output = tmp_path / family / "all.jsonl"
        records = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert records == [{"task_id": family}]


def test_main_skips_generated_style_checks_when_flag_set(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_suite",
        lambda family, seed, pool_size: [
            _FakeTask(f"{family}-{seed}-{pool_size}")
        ],
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE, "quota_report", lambda tasks, family: []
    )

    def _raise_assertion(tasks: list[_FakeTask]) -> None:  # noqa: ARG001
        raise AssertionError("should not run")

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        _raise_assertion,
    )

    generate_balanced_suites_main(
        output_dir=tmp_path,
        seed=3,
        pool_size=9,
        families="stateful",
        skip_generated_style_checks=True,
    )


def test_main_exits_when_generated_style_checks_fail(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "generate_suite",
        lambda family, seed, pool_size: [
            _FakeTask(f"{family}-{seed}-{pool_size}")
        ],
    )
    monkeypatch.setattr(
        _SCRIPT_MODULE, "quota_report", lambda tasks, family: []
    )

    def _raise_quality_error(tasks: list[_FakeTask]) -> None:  # noqa: ARG001
        raise _SCRIPT_MODULE.GeneratedCodeQualityError("bad generated code")

    monkeypatch.setattr(
        _SCRIPT_MODULE,
        "check_generated_code_quality",
        _raise_quality_error,
    )

    with pytest.raises(Exit) as exc_info:
        generate_balanced_suites_main(
            output_dir=tmp_path,
            seed=3,
            pool_size=9,
            families="stateful",
            skip_generated_style_checks=False,
        )

    assert exc_info.value.exit_code == 1
