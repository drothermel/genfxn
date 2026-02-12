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
        ast.Raise,
        # Boolean ops (composed predicates)
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.Not,
        # Comparisons
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Eq,
        ast.In,
        # Binary ops
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Mod,
        ast.BitAnd,
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
    {
        "abs",
        "int",
        "list",
        "max",
        "min",
        "ValueError",
        "__i32_wrap",
        "__i32_add",
        "__i32_mul",
        "__i32_neg",
        "__i32_abs",
        "__i32_clip",
        "__i32_mod",
    }
)

# Variable names used in rendered stateful code
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "xs",  # input param
        "x",  # loop variable
        "acc",  # conditional_linear_sum, toggle_sum
        "current_sum",  # resetting_best_prefix_sum
        "best_sum",  # resetting_best_prefix_sum
        "init",  # resetting_best_prefix_sum
        "current_run",  # longest_run
        "longest_run",  # longest_run
        "on",  # toggle_sum
        # int32 helper prelude locals/params
        "value",
        "lhs",
        "rhs",
        "low",
        "high",
        "divisor",
        "value_i32",
        "low_i32",
        "high_i32",
        "divisor_i32",
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
    "__i32_wrap": {1},
    "__i32_add": {2},
    "__i32_mul": {2},
    "__i32_neg": {1},
    "__i32_abs": {1},
    "__i32_clip": {3},
    "__i32_mod": {2},
}
