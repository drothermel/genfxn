"""AST safety checks for bitops code validation."""

import ast

ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Assign,
        ast.Return,
        ast.For,
        ast.If,
        ast.Expr,
        ast.Raise,
        ast.BinOp,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Dict,
        ast.Subscript,
        ast.Attribute,
        ast.Load,
        ast.Store,
        ast.BitAnd,
        ast.BitOr,
        ast.BitXor,
        ast.LShift,
        ast.RShift,
        ast.Sub,
        ast.Mod,
        ast.Invert,
        ast.Eq,
        ast.Is,
        ast.IsNot,
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

ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset({"int"})
