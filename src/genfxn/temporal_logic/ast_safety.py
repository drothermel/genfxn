"""AST safety scaffolding for temporal_logic validation."""

import ast

ALLOWED_AST_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Raise,
        ast.Return,
        ast.Assign,
        ast.If,
        ast.For,
        ast.Break,
        ast.Continue,
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
        ast.ListComp,
        ast.GeneratorExp,
        ast.comprehension,
        ast.Dict,
        ast.Tuple,
        ast.Subscript,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
        ast.USub,
        ast.Eq,
        ast.NotEq,
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
        "_eval",
        "_eval_predicate",
        "enumerate",
        "int",
        "len",
        "range",
        "str",
        "sum",
    }
)

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset()
ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "_eval",
        "_eval_predicate",
        "constant",
        "formula",
        "i",
        "idx",
        "j",
        "kind",
        "k",
        "n",
        "node",
        "op",
        "output_mode",
        "truth_values",
        "valid",
        "value",
        "xs",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "ValueError": {1},
    "enumerate": {1},
    "int": {1},
    "len": {1},
    "range": {1, 2, 3},
    "str": {1},
    "sum": {1},
    "_eval_predicate": {3},
    "_eval": {2},
}

METHOD_ARITIES: dict[str, set[int]] = {}
ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset(
    {"bool", "dict", "int", "list"}
)
