"""AST safety checks for stringrules code validation.

This module defines what AST nodes the stringrules renderer is expected to emit.
Notably, it needs ast.Attribute for method calls like s.lower(), s.startswith().

NOTE: This is not a security sandbox. It prevents accidental bad code and
obvious injection, not adversarial code execution.
"""

import ast

# Nodes the stringrules renderer actually emits
ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        # Module structure
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        # Control flow
        ast.If,
        ast.Return,
        # Expressions
        ast.Compare,
        ast.BinOp,
        ast.UnaryOp,  # For negative slices in reverse: s[::-1]
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Subscript,
        ast.Slice,
        ast.Attribute,  # For method calls: s.lower(), s.startswith()
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
        # Unary ops
        ast.USub,  # For -1 in slices
        # Contexts
        ast.Load,
    }
)

# Names allowed in function calls
ALLOWED_CALL_NAMES: frozenset[str] = frozenset({"len"})

# Methods allowed on string objects
ALLOWED_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "startswith",
        "endswith",
        "isalpha",
        "isdigit",
        "isupper",
        "islower",
        "lower",
        "upper",
        "capitalize",
        "swapcase",
        "replace",
        "strip",
        "find",
    }
)

# Runtime variable names allowed in rendered code (e.g. input param "s").
# Type annotations (e.g. def f(s: str) -> str:) are not checked here; see
# ALLOWED_ANNOTATION_NAMES and validate.py.
ALLOWED_VAR_NAMES: frozenset[str] = frozenset({"s"})

# Names allowed only in type annotations (arg.annotation, FunctionDef.returns).
ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset({"str"})

# Call arity requirements: function name -> allowed arg counts
CALL_ARITIES: dict[str, set[int]] = {
    "len": {1},
}

# Method arity requirements: method name -> allowed arg counts (excluding self).
# e.g. s.replace(old, new) -> 2, s.replace(old, new, count) -> 3.
METHOD_ARITIES: dict[str, set[int]] = {
    "startswith": {1, 2, 3},
    "endswith": {1, 2, 3},
    "replace": {2, 3},
    "strip": {0, 1},
    "find": {1, 2, 3},
    "lower": {0},
    "upper": {0},
    "capitalize": {0},
    "swapcase": {0},
    "isalpha": {0},
    "isdigit": {0},
    "isupper": {0},
    "islower": {0},
}
