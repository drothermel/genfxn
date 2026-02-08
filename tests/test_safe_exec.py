import pytest

from genfxn.core.safe_exec import SafeExecTimeoutError, execute_code_restricted


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
