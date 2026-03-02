"""AST safety checks for simple_algorithms code validation.

Defines AST nodes the simple_algorithms renderer is expected to emit.
Expand the whitelist intentionally when new expression forms are added.

IMPORTANT: If you change the renderer to emit new node types, update
this whitelist and the tests will catch any drift.

NOTE: This is not a security sandbox. It prevents accidental bad code and
obvious injection, not adversarial code execution.
"""

import ast

# Nodes the simple_algorithms renderer actually emits
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
        ast.Expr,
        ast.Compare,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Set,
        ast.Tuple,
        ast.Dict,
        ast.Subscript,
        ast.Slice,
        ast.ListComp,
        ast.SetComp,
        ast.comprehension,
        ast.GeneratorExp,
        ast.IfExp,
        ast.Attribute,
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
        ast.NotEq,
        ast.In,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Mod,
        ast.FloorDiv,
        ast.USub,
        ast.UAdd,
        ast.Load,
        ast.Store,
    }
)

# Names allowed in function calls
ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "int",
        "max",
        "min",
        "list",
        "len",
        "range",
        "sum",
        "set",
        "sorted",
        "tuple",
        "ValueError",
    }
)

# Methods allowed on objects (for .get, .items, .values, .add)
ALLOWED_METHOD_NAMES: frozenset[str] = frozenset(
    {"get", "items", "values", "keys", "add"}
)

METHOD_ARITIES: dict[str, set[int]] = {
    "get": {1, 2},
    "items": {0},
    "values": {0},
    "keys": {0},
    "add": {1},
}

# Variable names used in rendered simple_algorithms code
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "xs",
        "x",
        "i",
        "j",
        "val",
        "cnt",
        "pair",
        "counts",
        "max_count",
        "candidates",
        "count",
        "seen_pairs",
        "target",
        "window_sum",
        "max_sum",
    }
)

# Names allowed only in type annotations (arg.annotation, returns).
ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset({"int", "list"})

# Call arity requirements: function name -> allowed arg counts
CALL_ARITIES: dict[str, set[int]] = {
    "abs": {1},
    "int": {1},
    "max": {1, 2},
    "min": {1, 2},
    "list": {0, 1},
    "len": {1},
    "range": {1, 2, 3},
    "sum": {1},
    "set": {0, 1},
    "sorted": {1},
    "tuple": {1},
    "ValueError": {1},
}
