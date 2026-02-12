"""AST safety checks for sequence_dp code validation."""

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
        ast.Attribute,
        ast.ListComp,
        ast.comprehension,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.Mod,
        ast.LShift,
        ast.BitAnd,
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
        "RuntimeError",
        "ValueError",
        "_matches",
        "_pick",
        "_wrap_i64",
        "_unsigned_i64",
        "abs",
        "len",
        "max",
        "range",
    }
)

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset()

ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "a",
        "ai",
        "b",
        "best",
        "best_score",
        "bj",
        "candidate",
        "chosen",
        "delta",
        "diag",
        "dp",
        "g",
        "gap_score",
        "i",
        "j",
        "kind",
        "l",
        "left",
        "left_g",
        "left_l",
        "left_s",
        "m",
        "match_score",
        "mismatch_score",
        "move",
        "n",
        "options",
        "output_mode",
        "predicate",
        "prev_g",
        "prev_l",
        "prev_s",
        "result",
        "s",
        "template",
        "tie_order",
        "up",
        "up_g",
        "up_l",
        "up_s",
        "value",
        "i64_mask",
        "wrapped",
        "abs_diff",
        "x",
        "y",
        "zero",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "RuntimeError": {1},
    "ValueError": {1},
    "_matches": {2},
    "_pick": {3},
    "_wrap_i64": {1},
    "_unsigned_i64": {1},
    "abs": {1},
    "len": {1},
    "max": {2, 3},
    "range": {1, 2, 3},
}

METHOD_ARITIES: dict[str, set[int]] = {}

ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset(
    {
        "bool",
        "int",
        "list",
    }
)
