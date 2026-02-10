"""AST safety scaffolding for temporal_logic validation."""

import ast

ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.Assign,
        ast.If,
        ast.For,
        ast.Expr,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Dict,
        ast.Subscript,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
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
        "all",
        "any",
        "enumerate",
        "int",
        "len",
        "range",
        "sum",
    }
)

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset()
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "formula",
        "i",
        "idx",
        "j",
        "k",
        "n",
        "node",
        "op",
        "output_mode",
        "truth_values",
        "value",
        "xs",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "ValueError": {1},
    "all": {1},
    "any": {1},
    "enumerate": {1},
    "int": {1},
    "len": {1},
    "range": {1, 2, 3},
    "sum": {1},
}

METHOD_ARITIES: dict[str, set[int]] = {}
ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset({"dict", "int", "list"})
