import subprocess

import helpers
import pytest


def test_require_java_runtime_passes_when_tools_are_runnable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_which(name: str) -> str:
        return f"/usr/bin/{name}"

    calls: list[list[str]] = []

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        assert check is True
        assert capture_output is True
        assert text is True
        assert timeout == 5.0
        calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0)

    monkeypatch.setattr(helpers.shutil, "which", _fake_which)
    monkeypatch.setattr(helpers.subprocess, "run", _fake_run)

    assert helpers.require_java_runtime() == ("/usr/bin/javac", "/usr/bin/java")
    assert calls == [
        ["/usr/bin/javac", "-version"],
        ["/usr/bin/java", "-version"],
    ]


def test_require_java_runtime_fails_when_javac_not_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_which(name: str) -> str | None:
        if name == "javac":
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(helpers.shutil, "which", _fake_which)

    with pytest.raises(pytest.fail.Exception, match="javac not available"):
        helpers.require_java_runtime()


def test_require_java_runtime_fails_when_version_check_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_which(name: str) -> str:
        return f"/usr/bin/{name}"

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, cmd, stderr="runtime missing")

    monkeypatch.setattr(helpers.shutil, "which", _fake_which)
    monkeypatch.setattr(helpers.subprocess, "run", _fake_run)

    with pytest.raises(
        pytest.fail.Exception,
        match="javac found at /usr/bin/javac but failed health check",
    ):
        helpers.require_java_runtime()
