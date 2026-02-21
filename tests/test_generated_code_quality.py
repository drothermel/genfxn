import subprocess
from types import SimpleNamespace

import pytest

import genfxn.generated_code_quality as quality


def test_validate_required_tools_reports_missing_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(quality.shutil, "which", lambda tool: None)

    with pytest.raises(
        quality.GeneratedCodeQualityError,
        match="cargo, google-java-format, javac, rustfmt",
    ):
        quality._validate_required_tools()


def test_check_generated_code_quality_runs_java_and_rust_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = SimpleNamespace(
        task_id="task-1",
        family="piecewise",
        spec={"stub": True},
    )
    java_seen: list[str] = []
    rust_seen: list[str] = []

    monkeypatch.setattr(quality, "_validate_required_tools", lambda: None)
    monkeypatch.setattr(quality, "_validate_spec_for_task", lambda _: {"ok": 1})
    monkeypatch.setattr(
        quality,
        "_render_code",
        lambda task, language, spec_obj: (
            f"{task.task_id}-{language.value}-{spec_obj['ok']}"
        ),
    )
    monkeypatch.setattr(quality, "_check_java_code", java_seen.append)
    monkeypatch.setattr(quality, "_check_rust_code", rust_seen.append)

    quality.check_generated_code_quality([task])

    assert java_seen == ["task-1-java-1"]
    assert rust_seen == ["task-1-rust-1"]


def test_check_generated_code_quality_respects_family_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks = [
        SimpleNamespace(task_id="task-1", family="piecewise", spec={}),
        SimpleNamespace(task_id="task-2", family="stateful", spec={}),
    ]
    rendered_task_ids: list[str] = []

    monkeypatch.setattr(quality, "_validate_required_tools", lambda: None)
    monkeypatch.setattr(quality, "_validate_spec_for_task", lambda _: {})
    monkeypatch.setattr(
        quality,
        "_render_code",
        lambda task, language, spec_obj: (  # noqa: ARG005
            rendered_task_ids.append(f"{task.task_id}-{language.value}")
            or "code"
        ),
    )
    monkeypatch.setattr(quality, "_check_java_code", lambda code: None)
    monkeypatch.setattr(quality, "_check_rust_code", lambda code: None)

    quality.check_generated_code_quality(tasks, families={"stateful"})

    assert rendered_task_ids == ["task-2-java", "task-2-rust"]


def test_check_generated_code_quality_aggregates_subprocess_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = SimpleNamespace(task_id="task-1", family="piecewise", spec={})

    monkeypatch.setattr(quality, "_validate_required_tools", lambda: None)
    monkeypatch.setattr(quality, "_validate_spec_for_task", lambda _: {})
    monkeypatch.setattr(
        quality, "_render_code", lambda task, language, spec: "code"
    )
    monkeypatch.setattr(
        quality,
        "_check_java_code",
        lambda code: (_ for _ in ()).throw(
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["javac", "Main.java"],
                stderr="compile error",
            )
        ),
    )
    monkeypatch.setattr(quality, "_check_rust_code", lambda code: None)

    with pytest.raises(quality.GeneratedCodeQualityError) as exc_info:
        quality.check_generated_code_quality([task])

    message = str(exc_info.value)
    assert "task-1 (piecewise/java)" in message
    assert "compile error" in message
    assert "Use --skip-generated-style-checks" in message


def test_check_generated_code_quality_skips_unsupported_language_render(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = SimpleNamespace(task_id="task-1", family="piecewise", spec={})
    java_called = False
    rust_seen: list[str] = []

    def _fake_render(task, language, spec_obj):  # noqa: ARG001
        if language == quality.Language.JAVA:
            raise ValueError("unsupported")
        return "rust-code"

    def _fake_check_java(code: str) -> None:  # noqa: ARG001
        nonlocal java_called
        java_called = True

    monkeypatch.setattr(quality, "_validate_required_tools", lambda: None)
    monkeypatch.setattr(quality, "_validate_spec_for_task", lambda _: {})
    monkeypatch.setattr(quality, "_render_code", _fake_render)
    monkeypatch.setattr(quality, "_check_java_code", _fake_check_java)
    monkeypatch.setattr(quality, "_check_rust_code", rust_seen.append)

    quality.check_generated_code_quality([task])

    assert java_called is False
    assert rust_seen == ["rust-code"]
