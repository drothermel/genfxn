from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from typing import Any


class SafeExecTimeoutError(TimeoutError):
    """Raised when execution exceeds the configured timeout."""


class SafeExecExecutionError(RuntimeError):
    """Raised when isolated execution fails."""

    def __init__(self, error_type: str, error_message: str) -> None:
        super().__init__(f"{error_type}: {error_message}")
        self.error_type = error_type
        self.error_message = error_message


class SafeExecMissingFunctionError(SafeExecExecutionError):
    """Raised when function ``f`` is missing from the executed code."""


@dataclass
class _WorkerResult:
    ok: bool
    value: Any = None
    error_type: str | None = None
    error_message: str | None = None


def _set_memory_limit(memory_limit_mb: int | None) -> None:
    if memory_limit_mb is None:
        return
    try:
        import resource

        memory_bytes = memory_limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    except Exception:
        # Memory limits are platform-dependent; timeout remains enforced.
        return


def _exec_worker(
    queue: mp.Queue,
    code: str,
    allowed_builtins: dict[str, Any],
    call_args: tuple[Any, ...] | None,
    memory_limit_mb: int | None,
) -> None:
    _set_memory_limit(memory_limit_mb)
    globals_dict: dict[str, Any] = {"__builtins__": allowed_builtins}
    namespace: dict[str, Any] = {}

    try:
        exec(code, globals_dict, namespace)  # noqa: S102
        func = namespace.get("f")
        if func is None:
            raise NameError("Function 'f' not found in code namespace")
        if not callable(func):
            raise TypeError(f"Function 'f' is not callable: {type(func)}")

        if call_args is None:
            queue.put(_WorkerResult(ok=True, value=None))
            return

        queue.put(_WorkerResult(ok=True, value=func(*call_args)))
    except Exception as exc:
        queue.put(
            _WorkerResult(
                ok=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )


def _run_isolated(
    code: str,
    allowed_builtins: dict[str, Any],
    call_args: tuple[Any, ...] | None,
    timeout_sec: float,
    memory_limit_mb: int | None,
) -> Any:
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    process = ctx.Process(
        target=_exec_worker,
        args=(queue, code, allowed_builtins, call_args, memory_limit_mb),
    )
    process.start()
    process.join(timeout_sec)

    if process.is_alive():
        process.terminate()
        process.join()
        raise SafeExecTimeoutError(
            f"Code execution timed out after {timeout_sec} seconds"
        )

    if queue.empty():
        raise RuntimeError("Execution worker exited without a result")

    result: _WorkerResult = queue.get()
    if not result.ok:
        error_type = result.error_type or "RuntimeError"
        error_message = result.error_message or "Unknown execution error"
        if error_type == "NameError" and (
            error_message == "Function 'f' not found in code namespace"
        ):
            raise SafeExecMissingFunctionError(error_type, error_message)
        raise SafeExecExecutionError(error_type, error_message)
    return result.value


class _IsolatedFunction:
    def __init__(
        self,
        code: str,
        allowed_builtins: dict[str, Any],
        timeout_sec: float,
        memory_limit_mb: int | None,
    ) -> None:
        self._code = code
        self._allowed_builtins = allowed_builtins
        self._timeout_sec = timeout_sec
        self._memory_limit_mb = memory_limit_mb

    def __call__(self, *args: Any) -> Any:
        return _run_isolated(
            code=self._code,
            allowed_builtins=self._allowed_builtins,
            call_args=args,
            timeout_sec=self._timeout_sec,
            memory_limit_mb=self._memory_limit_mb,
        )


def execute_code_restricted(
    code: str,
    allowed_builtins: dict[str, Any],
    timeout_sec: float = 1.0,
    memory_limit_mb: int | None = 256,
) -> dict[str, Any]:
    """Execute untrusted code in an isolated process and return namespace.

    Returned namespace contains an isolated callable at key ``f`` that also
    executes in a separate process with the same limits.
    """
    _run_isolated(
        code=code,
        allowed_builtins=allowed_builtins,
        call_args=None,
        timeout_sec=timeout_sec,
        memory_limit_mb=memory_limit_mb,
    )
    return {
        "f": _IsolatedFunction(
            code=code,
            allowed_builtins=allowed_builtins,
            timeout_sec=timeout_sec,
            memory_limit_mb=memory_limit_mb,
        )
    }
