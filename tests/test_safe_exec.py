import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from genfxn.core import safe_exec
from genfxn.core.safe_exec import (
    SafeExecBootstrapError,
    SafeExecTimeoutError,
    SafeExecValidationError,
    execute_code_restricted,
)


def _spawn_sleep_and_record(path: str) -> int:
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"]
    )
    Path(path).write_text(str(proc.pid), encoding="utf-8")
    return proc.pid


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_execute_code_restricted_blocks_import() -> None:
    code = "def f(x):\n    return __import__('os').getcwd()"
    with pytest.raises(SafeExecValidationError, match="Rejected by static"):
        execute_code_restricted(code, {"len": len})


def test_execute_code_restricted_times_out_infinite_loop() -> None:
    code = "def f(x):\n    while True:\n        pass"
    fn = execute_code_restricted(code, {}, timeout_sec=0.2)["f"]
    with pytest.raises(SafeExecTimeoutError):
        fn(1)


def test_run_isolated_reports_worker_crash_exit_code(monkeypatch) -> None:
    class _FakeQueue:
        def get(self, timeout: float) -> object:
            raise safe_exec.Empty

    class _FakeProcess:
        exitcode = 7

        def start(self) -> None:
            return

        def join(self, timeout: float | None = None) -> None:
            return

        def is_alive(self) -> bool:
            return False

    class _FakeCtx:
        def get_start_method(self) -> str:
            return "spawn"

        def Queue(self) -> _FakeQueue:
            return _FakeQueue()

        def Process(self, target, args) -> _FakeProcess:  # noqa: ARG002
            return _FakeProcess()

    monkeypatch.setattr(
        safe_exec.mp, "get_context", lambda _: _FakeCtx()
    )

    with pytest.raises(RuntimeError, match="crashed with exit code 7"):
        safe_exec._run_isolated("def f(x):\n    return x", {}, (), 1.0, None)


def test_run_isolated_reports_missing_result_without_crash(monkeypatch) -> None:
    class _FakeQueue:
        def get(self, timeout: float) -> object:
            raise safe_exec.Empty

    class _FakeProcess:
        exitcode = 0

        def start(self) -> None:
            return

        def join(self, timeout: float | None = None) -> None:
            return

        def is_alive(self) -> bool:
            return False

    class _FakeCtx:
        def get_start_method(self) -> str:
            return "spawn"

        def Queue(self) -> _FakeQueue:
            return _FakeQueue()

        def Process(self, target, args) -> _FakeProcess:  # noqa: ARG002
            return _FakeProcess()

    monkeypatch.setattr(
        safe_exec.mp, "get_context", lambda _: _FakeCtx()
    )

    with pytest.raises(RuntimeError, match="exited without a result"):
        safe_exec._run_isolated("def f(x):\n    return x", {}, (), 1.0, None)


def test_persistent_worker_raises_bootstrap_error(monkeypatch) -> None:
    class _FakeProcess:
        def start(self) -> None:
            raise RuntimeError(
                "An attempt has been made to start a new process before the "
                "current process has finished its bootstrapping phase."
            )

    class _FakeQueue:
        def close(self) -> None:
            return

        def join_thread(self) -> None:
            return

    class _FakeCtx:
        def get_start_method(self) -> str:
            return "spawn"

        def Queue(self) -> _FakeQueue:
            return _FakeQueue()

        def Process(self, target, args) -> _FakeProcess:  # noqa: ARG002
            return _FakeProcess()

    monkeypatch.setattr(safe_exec, "_get_mp_context", lambda: _FakeCtx())

    with pytest.raises(SafeExecBootstrapError, match="__main__"):
        safe_exec._PersistentWorker(
            code="def f(x):\n    return x",
            allowed_builtins={},
            memory_limit_mb=None,
            timeout_sec=1.0,
        )


@pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX start-method preference is only relevant on POSIX",
)
def test_execute_code_restricted_works_in_script_without_main_guard(
    tmp_path: Path,
) -> None:
    script = tmp_path / "script.py"
    script.write_text(
        "from genfxn.core.safe_exec import execute_code_restricted\n"
        "fn = execute_code_restricted('def f(x):\\n    return x + 1', {}, "
        "timeout_sec=1.0)['f']\n"
        "print(fn(2))\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(script)],  # noqa: S607
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "3"


@pytest.mark.parametrize(
    "code",
    [
        "import os\ndef f(x):\n    return x",
        "def f(x):\n    return open('/tmp/owned').read()",
        "def f(x):\n    return x.__class__.__mro__",
    ],
)
def test_execute_code_restricted_rejects_adversarial_patterns(
    code: str,
) -> None:
    with pytest.raises(SafeExecValidationError, match="Rejected by static"):
        execute_code_restricted(code, {"len": len})


@pytest.mark.skipif(
    os.name != "posix",
    reason="Process-group descendant cleanup requires POSIX killpg",
)
def test_timeout_terminates_descendant_processes(tmp_path) -> None:
    pid_file = tmp_path / "child.pid"
    code = (
        "def f(path):\n"
        "    spawn(path)\n"
        "    while True:\n"
        "        pass"
    )
    fn = execute_code_restricted(
        code,
        {"spawn": _spawn_sleep_and_record},
        timeout_sec=0.2,
    )["f"]

    with pytest.raises(SafeExecTimeoutError):
        fn(str(pid_file))

    assert pid_file.exists()
    child_pid = int(pid_file.read_text(encoding="utf-8"))

    deadline = time.time() + 3.0
    while time.time() < deadline:
        if not _pid_exists(child_pid):
            break
        time.sleep(0.05)

    try:
        assert not _pid_exists(child_pid)
    finally:
        if _pid_exists(child_pid):
            os.kill(child_pid, signal.SIGKILL)


@pytest.mark.skipif(
    os.name != "posix",
    reason="Process-group descendant cleanup requires POSIX killpg",
)
def test_close_terminates_descendant_processes_after_shutdown(tmp_path) -> None:
    pid_file = tmp_path / "child.pid"
    code = "def f(path):\n    spawn(path)\n    return 1"
    fn = execute_code_restricted(
        code,
        {"spawn": _spawn_sleep_and_record},
        timeout_sec=1.0,
    )["f"]

    try:
        assert fn(str(pid_file)) == 1
        assert pid_file.exists()
        child_pid = int(pid_file.read_text(encoding="utf-8"))
    finally:
        fn.close()

    deadline = time.time() + 3.0
    while time.time() < deadline:
        if not _pid_exists(child_pid):
            break
        time.sleep(0.05)

    try:
        assert not _pid_exists(child_pid)
    finally:
        if _pid_exists(child_pid):
            os.kill(child_pid, signal.SIGKILL)
