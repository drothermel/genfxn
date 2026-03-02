"""AST safety checks for stateful code validation.

This module defines what AST nodes the stateful renderer is expected to emit.
The whitelist should be expanded intentionally when new expression forms
are added.

IMPORTANT: If you change the renderer to emit new node types, update this
whitelist and the tests will catch any drift.

NOTE: This is not a security sandbox. It prevents accidental bad code and
obvious injection, not adversarial code execution.
"""

import ast

# Nodes the stateful renderer actually emits
ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.For,
        ast.If,
        ast.Return,
        ast.Assign,
        ast.AugAssign,
        ast.Compare,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Set,
        ast.Raise,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Eq,
        ast.In,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Mod,
        ast.USub,
        ast.Subscript,
        ast.Load,
        ast.Store,
    }
)

# Names allowed in function calls
ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "int",
        "list",
        "max",
        "min",
        "ValueError",
    }
)

# Variable names used in rendered stateful code
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "xs",
        "x",
        "acc",
        "current_sum",
        "best_sum",
        "init",
        "current_run",
        "longest_run",
        "on",
    }
)

# Call arity requirements: function name -> allowed arg counts
CALL_ARITIES: dict[str, set[int]] = {
    "abs": {1},
    "int": {1},
    "max": {2},
    "min": {2},
    "list": {0, 1},
    "ValueError": {1},
}
