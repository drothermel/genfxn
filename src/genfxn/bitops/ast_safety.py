"""AST safety checks for bitops code validation."""

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
        ast.For,
        ast.If,
        ast.Expr,
        ast.Raise,
        ast.BinOp,
        ast.BoolOp,
        ast.IfExp,
        ast.UnaryOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Subscript,
        ast.Attribute,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.BitAnd,
        ast.BitOr,
        ast.BitXor,
        ast.LShift,
        ast.RShift,
        ast.Sub,
        ast.Mod,
        ast.Invert,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.Is,
        ast.IsNot,
        ast.And,
        ast.Or,
    }
)

ALLOWED_CALL_NAMES: frozenset[str] = frozenset({"ValueError"})

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset({"bit_count"})

ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "x",
        "width_bits",
        "mask",
        "operations",
        "value",
        "instruction",
        "op",
        "arg",
        "amt",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "ValueError": {1},
}

METHOD_ARITIES: dict[str, set[int]] = {
    "bit_count": {0},
}

ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset({"int", "None"})
