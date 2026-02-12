"""AST safety checks for piecewise code validation.

This module defines what AST nodes the piecewise renderer is expected to emit.
The whitelist should be expanded intentionally when new expression forms
are added.

IMPORTANT: If you change the renderer to emit new node types, update this
whitelist and the tests will catch any drift.

NOTE: This is not a security sandbox. It prevents accidental bad code and
obvious injection, not adversarial code execution.
"""

import ast

# Nodes the piecewise renderer actually emits
ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.If,
        ast.Return,
        ast.Assign,
        ast.Raise,
        ast.Compare,
        ast.Lt,
        ast.LtE,
        ast.Eq,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Mod,
        ast.BitAnd,
        ast.UnaryOp,
        ast.USub,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Load,
        ast.Store,
    }
)

# Names used in function calls and type annotations
ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "int",
        "ValueError",
        "__i32_wrap",
        "__i32_add",
        "__i32_mul",
        "__i32_abs",
        "__i32_mod",
    }
)

# Variable names used in int32 helper prelude and rendered function body.
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "value",
        "lhs",
        "rhs",
        "divisor",
        "value_i32",
        "divisor_i32",
    }
)

# Call arity requirements: function name -> allowed arg counts.
CALL_ARITIES: dict[str, set[int]] = {
    "abs": {1},
    "int": {1},
    "ValueError": {1},
    "__i32_wrap": {1},
    "__i32_add": {2},
    "__i32_mul": {2},
    "__i32_abs": {1},
    "__i32_mod": {2},
}
