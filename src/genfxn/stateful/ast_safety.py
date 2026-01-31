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
        # Module structure
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        # Control flow
        ast.For,
        ast.If,
        ast.Return,
        # Statements
        ast.Assign,
        ast.AugAssign,
        # Expressions
        ast.Compare,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Set,
        # Comparisons
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Eq,
        # Binary ops
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Mod,
        # Unary ops
        ast.USub,
        # Type annotations
        ast.Subscript,
        # Contexts
        ast.Load,
        ast.Store,
    }
)

# Names allowed in function calls
ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {"abs", "int", "max", "min", "list"}
)

# Variable names used in rendered stateful code
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "xs",  # input param
        "x",  # loop variable
        "acc",  # conditional_linear_sum
        "current_sum",  # resetting_best_prefix_sum
        "best_sum",  # resetting_best_prefix_sum
        "current_run",  # longest_run
        "longest_run",  # longest_run
    }
)

# Call arity requirements: function name -> allowed arg counts
CALL_ARITIES: dict[str, set[int]] = {
    "abs": {1},
    "int": {1},
    "max": {2},
    "min": {2},
    "list": {0, 1},
}
