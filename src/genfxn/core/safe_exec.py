from typing import Any


def execute_code_restricted(
    code: str, allowed_builtins: dict[str, Any]
) -> dict[str, Any]:
    """Execute code with restricted builtins and return resulting namespace."""
    globals_dict: dict[str, Any] = {"__builtins__": allowed_builtins}
    namespace: dict[str, Any] = {}
    exec(code, globals_dict, namespace)  # noqa: S102
    return namespace
