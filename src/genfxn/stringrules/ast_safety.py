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
    }
)

# Variable names used in rendered stringrules code
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "s",  # input param
        "str",  # type annotation
    }
)

# Call arity requirements: function name -> allowed arg counts
CALL_ARITIES: dict[str, set[int]] = {
    "len": {1},
}
