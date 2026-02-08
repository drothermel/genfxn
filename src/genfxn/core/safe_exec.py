from __future__ import annotations

import ast
import multiprocessing as mp
import os
import signal
from dataclasses import dataclass
from queue import Empty
from typing import Any


class SafeExecValidationError(ValueError):
    """Raised when code fails static safety validation."""


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


def _validate_untrusted_code(code: str) -> None:
    """Best-effort static hardening for untrusted code.

    This is not a security sandbox. It blocks known-dangerous patterns but
    cannot provide complete containment against Python escapes.
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise SafeExecValidationError(
            f"Invalid Python syntax at line {exc.lineno}: {exc.msg}"
        ) from exc

    blocked_calls = {
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
    }
    blocked_attrs = {
        "__subclasses__",
        "__globals__",
        "__code__",
        "__getattribute__",
        "__mro__",
    }
    blocked_nodes = (
        ast.Import,
        ast.ImportFrom,
        ast.ClassDef,
        ast.Global,
        ast.Nonlocal,
    )

    errors: list[str] = []
    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        if not isinstance(stmt, ast.FunctionDef):
            errors.append(
                "Top-level statements are limited to function definitions"
            )
            continue
    for node in ast.walk(tree):
        if isinstance(node, blocked_nodes):
            errors.append(f"Disallowed syntax node: {type(node).__name__}")
            continue

        if isinstance(node, ast.Name) and (
            node.id in blocked_calls
            or (node.id.startswith("__") and node.id.endswith("__"))
        ):
            errors.append(f"Disallowed identifier: {node.id}")
            continue

        if isinstance(node, ast.Attribute):
            if node.attr in blocked_attrs or (
                node.attr.startswith("__") and node.attr.endswith("__")
            ):
                errors.append(f"Disallowed attribute access: {node.attr}")
                continue

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and (
                node.func.id in blocked_calls
            ):
                errors.append(f"Disallowed call: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and (
                node.func.attr in blocked_attrs
            ):
                errors.append(f"Disallowed call attribute: {node.func.attr}")

    if errors:
        unique = list(dict.fromkeys(errors))
        summary = "; ".join(unique[:3])
        if len(unique) > 3:
            summary += f"; ... ({len(unique)} issues)"
        raise SafeExecValidationError(
            f"Rejected by static validation: {summary}"
        )


def _set_process_group() -> None:
    if os.name != "posix":
        return
    try:
        os.setsid()
    except Exception:
        return


def _terminate_process_tree(process: mp.Process) -> None:
    if not process.is_alive():
        return

    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except Exception:
            pass
        process.join(timeout=0.2)
        if process.is_alive():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                pass
            process.join(timeout=0.2)

    if process.is_alive():
        try:
            process.terminate()
        except Exception:
            pass
        process.join(timeout=0.2)

    if process.is_alive():
        try:
            process.kill()
        except Exception:
            pass
        process.join(timeout=0.2)


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
    _set_process_group()
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
    _validate_untrusted_code(code)
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    process = ctx.Process(
        target=_exec_worker,
        args=(queue, code, allowed_builtins, call_args, memory_limit_mb),
    )
    process.start()
    process.join(timeout_sec)

    if process.is_alive():
        _terminate_process_tree(process)
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
    _set_process_group()
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
        _terminate_process_tree(self._process)

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
    """Execute untrusted code in a constrained subprocess and return namespace.

    Returned namespace contains an isolated callable at key ``f`` that also
    executes in a separate process with the same limits.

    Important: this is defense-in-depth for robustness, not a true security
    sandbox. Do not run adversarial code without OS/container isolation.
    """
    _validate_untrusted_code(code)
    return {
        "f": _IsolatedFunction(
            code=code,
            allowed_builtins=allowed_builtins,
            timeout_sec=timeout_sec,
            memory_limit_mb=memory_limit_mb,
        )
    }
