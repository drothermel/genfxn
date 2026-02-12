from __future__ import annotations

import ast
import atexit
import errno
import logging
import math
import multiprocessing as mp
import os
import pickle
import signal
import time
from dataclasses import dataclass
from queue import Empty
from typing import Any, cast

_LOGGER = logging.getLogger(__name__)


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


class SafeExecBootstrapError(RuntimeError):
    """Raised when multiprocessing bootstrap requirements are not met."""


class SafeExecTrustRequiredError(PermissionError):
    """Raised when executing untrusted code without explicit trust opt-in."""


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


def _can_kill_process_group(pid: int | None) -> bool:
    if os.name != "posix" or pid is None or pid <= 0:
        return False
    try:
        return os.getpgid(pid) == pid
    except ProcessLookupError:
        return False
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        return False
    except Exception:
        return False


def _terminate_process_tree(process: mp.Process) -> None:
    pid = process.pid
    can_killpg = os.name == "posix" and pid is not None and pid > 0
    # If the worker is still alive, only use killpg when it is clearly a
    # process-group leader. If it already exited, keep the historical killpg
    # attempt so lingering descendants in that group are still cleaned up.
    if can_killpg and process.is_alive():
        can_killpg = _can_kill_process_group(pid)

    def _killpg(sig: signal.Signals) -> None:
        if not can_killpg or pid is None or pid <= 0:
            return
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return
        except OSError as exc:
            if exc.errno == errno.ESRCH:
                return
        except Exception:
            return

    if os.name == "posix":
        # On POSIX, always attempt process-group termination by PID to clean
        # descendants even if the worker parent has already exited.
        _killpg(signal.SIGTERM)
        if process.is_alive():
            process.join(timeout=0.2)
        if process.is_alive():
            _killpg(signal.SIGKILL)
            process.join(timeout=0.2)
    elif not process.is_alive():
        return

    if process.is_alive():
        try:
            process.terminate()
        except Exception:
            _LOGGER.debug(
                "safe_exec cleanup: process.terminate() failed",
                exc_info=True,
            )
        process.join(timeout=0.2)

    if process.is_alive():
        try:
            process.kill()
        except Exception:
            _LOGGER.debug(
                "safe_exec cleanup: process.kill() failed",
                exc_info=True,
            )
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


_SAFE_EXEC_START_METHOD_ENV = "GENFXN_SAFE_EXEC_START_METHOD"
_DEFAULT_MAX_RESULT_BYTES = 1_000_000
_RESULT_QUEUE_GRACE_SEC = 0.25
_RESULT_QUEUE_POLL_SEC = 0.05
_PERSISTENT_STARTUP_TIMEOUT_FLOOR_SEC = 1.0
_MAX_RESULT_NESTING_DEPTH = 32


def _persistent_startup_timeout_sec(timeout_sec: float) -> float:
    return max(timeout_sec, _PERSISTENT_STARTUP_TIMEOUT_FLOOR_SEC)


def _validate_execution_limits(
    *,
    timeout_sec: float,
    memory_limit_mb: int | None,
    max_result_bytes: int | None,
) -> None:
    if (
        isinstance(timeout_sec, bool)
        or not isinstance(timeout_sec, int | float)
        or not math.isfinite(timeout_sec)
        or timeout_sec <= 0
    ):
        raise ValueError("timeout_sec must be a finite number > 0")

    if memory_limit_mb is not None and (
        isinstance(memory_limit_mb, bool)
        or not isinstance(memory_limit_mb, int)
        or memory_limit_mb <= 0
    ):
        raise ValueError("memory_limit_mb must be a positive integer or None")

    if max_result_bytes is not None and (
        isinstance(max_result_bytes, bool)
        or not isinstance(max_result_bytes, int)
        or max_result_bytes <= 0
    ):
        raise ValueError(
            "max_result_bytes must be a positive integer or None"
        )


def _is_spawn_bootstrap_error(exc: BaseException) -> bool:
    msg = str(exc)
    return (
        isinstance(exc, RuntimeError)
        and "start a new process before the" in msg
        and "bootstrapping phase" in msg
    )


def _bootstrap_error(method: str, exc: BaseException) -> SafeExecBootstrapError:
    return SafeExecBootstrapError(
        "safe_exec multiprocessing bootstrap failed while using "
        f"start method '{method}'. If this is a script entry point, wrap "
        "execution in `if __name__ == '__main__':` (plus "
        "`freeze_support()` when needed), or on POSIX use "
        f"`{_SAFE_EXEC_START_METHOD_ENV}=fork`. Original error: {exc}"
    )


def _is_spawn_like_method(method: str) -> bool:
    return method in {"spawn", "forkserver"}


def _has_importable_main_module() -> bool:
    try:
        import __main__
    except Exception:
        return False

    main_file = getattr(__main__, "__file__", None)
    if not isinstance(main_file, str) or not main_file:
        return False

    # `spawn`/`forkserver` need an importable script file. Interactive modes
    # (`<stdin>`, `<string>`, REPL) do not satisfy this requirement.
    if main_file.startswith("<") and main_file.endswith(">"):
        return False
    return True


def _should_map_startup_crash_to_bootstrap_error(method: str) -> bool:
    return _is_spawn_like_method(method) and not _has_importable_main_module()


def _get_mp_context() -> mp.context.BaseContext:
    """Return multiprocessing context suitable for safe_exec workers."""
    configured = os.environ.get(_SAFE_EXEC_START_METHOD_ENV)
    allowed = set(mp.get_all_start_methods())

    if configured:
        if configured not in allowed:
            valid = ", ".join(sorted(allowed))
            raise ValueError(
                f"Invalid {_SAFE_EXEC_START_METHOD_ENV}={configured!r}. "
                f"Valid values: {valid}"
            )
        return mp.get_context(configured)

    # Default to spawn/forkserver to avoid fork-safety issues in
    # multi-threaded hosts.
    if os.name == "posix":
        if "forkserver" in allowed:
            return mp.get_context("forkserver")
        if "spawn" in allowed:
            return mp.get_context("spawn")
    return mp.get_context("spawn")


def _exec_worker(
    queue: mp.Queue,
    code: str,
    allowed_builtins: dict[str, Any],
    call_args: tuple[Any, ...] | None,
    memory_limit_mb: int | None,
    max_result_bytes: int | None,
) -> None:
    _set_process_group()
    _set_memory_limit(memory_limit_mb)
    execution_env: dict[str, Any] = {"__builtins__": allowed_builtins}

    try:
        exec(code, execution_env, execution_env)  # noqa: S102
        func = execution_env.get("f")
        if func is None:
            raise NameError("Function 'f' not found in code namespace")
        if not callable(func):
            raise TypeError(f"Function 'f' is not callable: {type(func)}")

        if call_args is None:
            _put_worker_result(
                queue,
                _WorkerResult(ok=True, value=None),
                max_result_bytes,
            )
            return

        _put_worker_result(
            queue,
            _WorkerResult(ok=True, value=func(*call_args)),
            max_result_bytes,
        )
    except Exception as exc:
        _put_worker_result(
            queue,
            _WorkerResult(
                ok=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            ),
            max_result_bytes,
        )


def _sanitize_worker_result_value(value: Any, depth: int = 0) -> Any:
    if depth > _MAX_RESULT_NESTING_DEPTH:
        raise TypeError("Worker result exceeded maximum nesting depth")

    if (
        value is None
        or isinstance(value, bool)
        or isinstance(value, int)
        or isinstance(value, float)
        or isinstance(value, str)
    ):
        return value

    if isinstance(value, list):
        return [
            _sanitize_worker_result_value(item, depth + 1)
            for item in value
        ]

    if isinstance(value, tuple):
        return tuple(
            _sanitize_worker_result_value(item, depth + 1)
            for item in value
        )

    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            if not (
                key is None
                or isinstance(key, bool)
                or isinstance(key, int)
                or isinstance(key, float)
                or isinstance(key, str)
            ):
                raise TypeError(
                    "Unsupported worker result dict key type: "
                    f"{type(key).__name__}"
                )
            sanitized[key] = _sanitize_worker_result_value(item, depth + 1)
        return sanitized

    raise TypeError(f"Unsupported worker result type: {type(value).__name__}")


def _put_worker_result(
    queue: mp.Queue,
    result: _WorkerResult,
    max_result_bytes: int | None,
) -> None:
    sanitized_result = result
    if result.ok:
        try:
            sanitized_result = _WorkerResult(
                ok=True,
                value=_sanitize_worker_result_value(result.value),
            )
        except Exception as exc:
            queue.put(
                _WorkerResult(
                    ok=False,
                    error_type="RuntimeError",
                    error_message=(
                        "Failed to serialize worker result: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                )
            )
            return

    # Always pre-serialize to surface serialization failures synchronously.
    # Otherwise Queue feeder-thread errors can be misreported as timeouts.
    try:
        payload = pickle.dumps(
            sanitized_result,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    except Exception as exc:
        queue.put(
            _WorkerResult(
                ok=False,
                error_type="RuntimeError",
                error_message=(
                    "Failed to serialize worker result: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )
        )
        return

    if max_result_bytes is not None:
        payload_size = len(payload)
        if payload_size > max_result_bytes:
            queue.put(
                _WorkerResult(
                    ok=False,
                    error_type="RuntimeError",
                    error_message=(
                        "Worker result exceeded max_result_bytes "
                        f"({payload_size} > {max_result_bytes})"
                    ),
                )
            )
            return
    queue.put(sanitized_result)


def _run_isolated(
    code: str,
    allowed_builtins: dict[str, Any],
    call_args: tuple[Any, ...] | None,
    timeout_sec: float,
    memory_limit_mb: int | None,
    max_result_bytes: int | None = _DEFAULT_MAX_RESULT_BYTES,
) -> Any:
    _validate_untrusted_code(code)
    ctx = _get_mp_context()
    ctx_runtime = cast(Any, ctx)
    method = ctx.get_start_method()
    queue: mp.Queue = ctx_runtime.Queue()
    process = ctx_runtime.Process(
        target=_exec_worker,
        args=(
            queue,
            code,
            allowed_builtins,
            call_args,
            memory_limit_mb,
            max_result_bytes,
        ),
    )
    try:
        process.start()
    except Exception as exc:
        if _is_spawn_bootstrap_error(exc):
            raise _bootstrap_error(method, exc) from exc
        raise

    deadline = time.monotonic() + timeout_sec
    result: _WorkerResult | None = None
    while result is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        timeout = min(_RESULT_QUEUE_POLL_SEC, remaining)
        try:
            result = queue.get(timeout=timeout)
        except Empty:
            if not process.is_alive():
                break

    if result is None and process.is_alive():
        _terminate_process_tree(process)
        raise SafeExecTimeoutError(
            f"Code execution timed out after {timeout_sec} seconds"
        )

    if result is None:
        deadline = time.monotonic() + _RESULT_QUEUE_GRACE_SEC
        while result is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            timeout = min(_RESULT_QUEUE_POLL_SEC, remaining)
            try:
                result = queue.get(timeout=timeout)
            except Empty:
                continue

    if result is None:
        if process.exitcode not in (None, 0):
            raise RuntimeError(
                f"Execution worker crashed with exit code {process.exitcode}"
            )
        raise RuntimeError("Execution worker exited without a result")

    process.join(timeout=0)

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
        max_result_bytes: int | None = _DEFAULT_MAX_RESULT_BYTES,
    ) -> None:
        self._closed = False
        self._worker = _PersistentWorker(
            code=code,
            allowed_builtins=allowed_builtins,
            memory_limit_mb=memory_limit_mb,
            timeout_sec=timeout_sec,
            max_result_bytes=max_result_bytes,
        )
        self._timeout_sec = timeout_sec
        atexit.register(self.close)

    def __call__(self, *args: Any) -> Any:
        return self._worker.call(args, self._timeout_sec)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            atexit.unregister(self.close)
        except Exception:
            _LOGGER.debug(
                "safe_exec cleanup: atexit.unregister() failed",
                exc_info=True,
            )
        self._worker.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            _LOGGER.debug(
                "safe_exec cleanup: __del__ close() failed",
                exc_info=True,
            )


def _persistent_worker(
    request_queue: mp.Queue,
    response_queue: mp.Queue,
    code: str,
    allowed_builtins: dict[str, Any],
    memory_limit_mb: int | None,
    max_result_bytes: int | None,
) -> None:
    _set_process_group()
    _set_memory_limit(memory_limit_mb)
    execution_env: dict[str, Any] = {"__builtins__": allowed_builtins}

    try:
        exec(code, execution_env, execution_env)  # noqa: S102
        func = execution_env.get("f")
        if func is None:
            raise NameError("Function 'f' not found in code namespace")
        if not callable(func):
            raise TypeError(f"Function 'f' is not callable: {type(func)}")
        _put_worker_result(
            response_queue,
            _WorkerResult(ok=True, value=None),
            max_result_bytes,
        )
    except Exception as exc:
        _put_worker_result(
            response_queue,
            _WorkerResult(
                ok=False,
                error_type=type(exc).__name__,
                error_message=str(exc),
            ),
            max_result_bytes,
        )
        return

    while True:
        req: _WorkerRequest = request_queue.get()
        if req.kind == "shutdown":
            return
        if req.kind != "call":
            _put_worker_result(
                response_queue,
                _WorkerResult(
                    ok=False,
                    error_type="RuntimeError",
                    error_message=f"Unknown request kind: {req.kind}",
                ),
                max_result_bytes,
            )
            continue

        try:
            args = req.call_args if req.call_args is not None else ()
            _put_worker_result(
                response_queue,
                _WorkerResult(ok=True, value=func(*args)),
                max_result_bytes,
            )
        except Exception as exc:
            _put_worker_result(
                response_queue,
                _WorkerResult(
                    ok=False,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                ),
                max_result_bytes,
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
        max_result_bytes: int | None = _DEFAULT_MAX_RESULT_BYTES,
    ) -> None:
        self._ctx = _get_mp_context()
        ctx_runtime = cast(Any, self._ctx)
        self._start_method = self._ctx.get_start_method()
        self._request_queue: mp.Queue = ctx_runtime.Queue()
        self._response_queue: mp.Queue = ctx_runtime.Queue()
        self._process = ctx_runtime.Process(
            target=_persistent_worker,
            args=(
                self._request_queue,
                self._response_queue,
                code,
                allowed_builtins,
                memory_limit_mb,
                max_result_bytes,
            ),
        )
        try:
            self._process.start()
        except Exception as exc:
            if _is_spawn_bootstrap_error(exc):
                raise _bootstrap_error(self._start_method, exc) from exc
            raise

        try:
            startup_timeout_sec = _persistent_startup_timeout_sec(timeout_sec)
            init_result: _WorkerResult = self._response_queue.get(
                timeout=startup_timeout_sec
            )
        except Empty:
            self._terminate()
            if self._process.exitcode not in (None, 0):
                if _should_map_startup_crash_to_bootstrap_error(
                    self._start_method
                ):
                    raise _bootstrap_error(
                        self._start_method,
                        RuntimeError(
                            "worker exited during startup with exit code "
                            f"{self._process.exitcode}"
                        ),
                    )
                raise RuntimeError(
                    "Execution worker crashed during startup with "
                    f"exit code {self._process.exitcode}"
                )
            raise SafeExecTimeoutError(
                "Code execution startup timed out after "
                f"{startup_timeout_sec} seconds"
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
            if not self._process.is_alive():
                exit_code = self._process.exitcode
                self._terminate()
                raise RuntimeError(
                    f"Execution worker crashed with exit code {exit_code}"
                )
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
                    _LOGGER.debug(
                        "safe_exec cleanup: worker shutdown signal failed",
                        exc_info=True,
                    )
                self._terminate()
        finally:
            for q in (self._request_queue, self._response_queue):
                try:
                    q.close()
                except Exception:
                    _LOGGER.debug(
                        "safe_exec cleanup: queue.close() failed",
                        exc_info=True,
                    )
                try:
                    q.join_thread()
                except Exception:
                    _LOGGER.debug(
                        "safe_exec cleanup: queue.join_thread() failed",
                        exc_info=True,
                    )


def execute_code_restricted(
    code: str,
    allowed_builtins: dict[str, Any],
    timeout_sec: float = 1.0,
    memory_limit_mb: int | None = 256,
    *,
    trust_untrusted_code: bool = False,
    max_result_bytes: int | None = _DEFAULT_MAX_RESULT_BYTES,
) -> dict[str, Any]:
    """Execute untrusted code in a constrained subprocess and return namespace.

    Returned namespace contains an isolated callable at key ``f`` that also
    executes in a separate process with the same limits.

    Important: this is defense-in-depth for robustness, not a true security
    sandbox. Do not run adversarial code without OS/container isolation.
    """
    if not trust_untrusted_code:
        raise SafeExecTrustRequiredError(
            "Refusing to execute untrusted code without explicit trust. "
            "Pass trust_untrusted_code=True only for trusted inputs."
        )

    _validate_execution_limits(
        timeout_sec=timeout_sec,
        memory_limit_mb=memory_limit_mb,
        max_result_bytes=max_result_bytes,
    )
    _validate_untrusted_code(code)
    return {
        "f": _IsolatedFunction(
            code=code,
            allowed_builtins=allowed_builtins,
            timeout_sec=timeout_sec,
            memory_limit_mb=memory_limit_mb,
            max_result_bytes=max_result_bytes,
        )
    }
