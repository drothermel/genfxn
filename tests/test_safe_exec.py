import pytest

from genfxn.core import safe_exec
from genfxn.core.safe_exec import (
    SafeExecTimeoutError,
    execute_code_restricted,
)


def test_execute_code_restricted_blocks_import() -> None:
    code = "def f(x):\n    return __import__('os').getcwd()"
    fn = execute_code_restricted(code, {"len": len})["f"]
    with pytest.raises(RuntimeError, match="NameError"):
        fn(1)


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
        def Queue(self) -> _FakeQueue:
            return _FakeQueue()

        def Process(self, target, args) -> _FakeProcess:  # noqa: ARG002
            return _FakeProcess()

    monkeypatch.setattr(
        safe_exec.mp, "get_context", lambda _: _FakeCtx()
    )

    with pytest.raises(RuntimeError, match="exited without a result"):
        safe_exec._run_isolated("def f(x):\n    return x", {}, (), 1.0, None)
