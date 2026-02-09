"""AST safety checks for intervals code validation."""

import ast

ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Assign,
        ast.AnnAssign,
        ast.AugAssign,
        ast.Return,
        ast.Raise,
        ast.If,
        ast.For,
        ast.Expr,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.IfExp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Subscript,
        ast.Slice,
        ast.Attribute,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.USub,
        ast.Eq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.And,
        ast.Or,
        ast.Not,
    }
)

ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "ValueError",
        "len",
        "max",
        "min",
        "range",
        "sorted",
    }
)

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "append",
        "get",
        "sort",
    }
)

ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "active",
        "adjusted",
        "best",
        "boundary_mode",
        "end",
        "events",
        "gaps",
        "hi",
        "idx",
        "intervals",
        "lo",
        "merge_touching",
        "merged",
        "next_point",
        "next_start",
        "operation",
        "point",
        "prev_end",
        "prev_start",
        "raw_a",
        "raw_b",
        "start",
        "threshold",
        "total",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "ValueError": {1},
    "len": {1},
    "max": {2},
    "min": {2},
    "range": {1, 2, 3},
    "sorted": {1},
}

METHOD_ARITIES: dict[str, set[int]] = {
    "append": {1},
    "get": {2},
    "sort": {0},
}

ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset(
    {
        "dict",
        "int",
        "list",
        "tuple",
    }
)
