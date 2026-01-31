"""AST safety checks for piecewise code validation.

This module defines what AST nodes the piecewise renderer is expected to emit.
The whitelist should be expanded intentionally when new expression forms are added.

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
        ast.Compare,
        ast.Lt,
        ast.LtE,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Mod,
        ast.UnaryOp,
        ast.USub,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Load,
    }
)

# Names used in function calls and type annotations
ALLOWED_CALL_NAMES: frozenset[str] = frozenset({"abs", "int"})
