from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass
from queue import Empty
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


@dataclass
class _WorkerRequest:
    kind: str
    call_args: tuple[Any, ...] | None = None


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

    try:
        result: _WorkerResult = queue.get(timeout=0.1)
    except Empty:
        if process.exitcode not in (None, 0):
            raise RuntimeError(
                f"Execution worker crashed with exit code {process.exitcode}"
            )
        raise RuntimeError("Execution worker exited without a result")
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
        self._worker = _PersistentWorker(
            code=code,
            allowed_builtins=allowed_builtins,
            memory_limit_mb=memory_limit_mb,
            timeout_sec=timeout_sec,
        )
        self._timeout_sec = timeout_sec

    def __call__(self, *args: Any) -> Any:
        return self._worker.call(args, self._timeout_sec)

    def close(self) -> None:
        self._worker.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def _persistent_worker(
    request_queue: mp.Queue,
    response_queue: mp.Queue,
    code: str,
    allowed_builtins: dict[str, Any],
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
        response_queue.put(_WorkerResult(ok=True, value=None))
    except Exception as exc:
        response_queue.put(
            _WorkerResult(
                ok=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        )
        return

    while True:
        req: _WorkerRequest = request_queue.get()
        if req.kind == "shutdown":
            return
        if req.kind != "call":
            response_queue.put(
                _WorkerResult(
                    ok=False,
                    error_type="RuntimeError",
                    error_message=f"Unknown request kind: {req.kind}",
                )
            )
            continue

        try:
            args = req.call_args if req.call_args is not None else ()
            response_queue.put(_WorkerResult(ok=True, value=func(*args)))
        except Exception as exc:
            response_queue.put(
                _WorkerResult(
                    ok=False,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )


def _raise_from_worker_result(result: _WorkerResult) -> None:
    error_type = result.error_type or "RuntimeError"
    error_message = result.error_message or "Unknown execution error"
    if error_type == "NameError" and (
        error_message == "Function 'f' not found in code namespace"
    ):
        raise SafeExecMissingFunctionError(error_type, error_message)
    raise SafeExecExecutionError(error_type, error_message)


class _PersistentWorker:
    def __init__(
        self,
        code: str,
        allowed_builtins: dict[str, Any],
        memory_limit_mb: int | None,
        timeout_sec: float,
    ) -> None:
        self._ctx = mp.get_context("spawn")
        self._request_queue: mp.Queue = self._ctx.Queue()
        self._response_queue: mp.Queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_persistent_worker,
            args=(
                self._request_queue,
                self._response_queue,
                code,
                allowed_builtins,
                memory_limit_mb,
            ),
        )
        self._process.start()

        try:
            init_result: _WorkerResult = self._response_queue.get(
                timeout=timeout_sec
            )
        except Empty:
            self._terminate()
            raise SafeExecTimeoutError(
                f"Code execution timed out after {timeout_sec} seconds"
            )

        if not init_result.ok:
            self._terminate()
            _raise_from_worker_result(init_result)

    def call(self, args: tuple[Any, ...], timeout_sec: float) -> Any:
        if not self._process.is_alive():
            exit_code = self._process.exitcode
            raise RuntimeError(
                f"Execution worker crashed with exit code {exit_code}"
            )

        self._request_queue.put(_WorkerRequest(kind="call", call_args=args))
        try:
            result: _WorkerResult = self._response_queue.get(
                timeout=timeout_sec
            )
        except Empty:
            self._terminate()
            raise SafeExecTimeoutError(
                f"Code execution timed out after {timeout_sec} seconds"
            )

        if not result.ok:
            _raise_from_worker_result(result)
        return result.value

    def _terminate(self) -> None:
        if self._process.is_alive():
            self._process.terminate()
            self._process.join()

    def close(self) -> None:
        try:
            if self._process.is_alive():
                try:
                    self._request_queue.put_nowait(
                        _WorkerRequest(kind="shutdown")
                    )
                    self._process.join(timeout=0.2)
                except Exception:
                    pass
                self._terminate()
        finally:
            for q in (self._request_queue, self._response_queue):
                try:
                    q.close()
                except Exception:
                    pass
                try:
                    q.join_thread()
                except Exception:
                    pass


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
    return {
        "f": _IsolatedFunction(
            code=code,
            allowed_builtins=allowed_builtins,
            timeout_sec=timeout_sec,
            memory_limit_mb=memory_limit_mb,
        )
    }
