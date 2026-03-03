from __future__ import annotations

from collections.abc import Callable

from genfxn.types import DEFAULT_STR_INPUT_VAR


def eval_guarded_str_expr(input: str, str_fxn: Callable[[str], str]) -> str:
    return input if len(input) == 0 else str_fxn(input)


def render_guarded_str_method(method_name: str) -> str:
    input_var = DEFAULT_STR_INPUT_VAR
    return (
        f"{input_var} if len({input_var}) == 0 else {input_var}.{method_name}()"
    )


def render_guarded_str_method_with_args(method_name: str, args: str) -> str:
    input_var = DEFAULT_STR_INPUT_VAR
    return (
        f"{input_var} if len({input_var}) == 0 "
        f"else {input_var}.{method_name}({args})"
    )


def render_guarded_str_expr(expr: str) -> str:
    input_var = DEFAULT_STR_INPUT_VAR
    return f"{input_var} if len({input_var}) == 0 else {expr}"


def render_guarded_str_suffix(suffix: str) -> str:
    input_var = DEFAULT_STR_INPUT_VAR
    return f"{input_var} if len({input_var}) == 0 else {input_var}{suffix}"
