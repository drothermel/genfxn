"""AST safety checks for FSM code validation."""

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
        ast.Continue,
        ast.Break,
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
        ast.Set,
        ast.Tuple,
        ast.Dict,
        ast.Subscript,
        ast.Attribute,
        ast.Lambda,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
        ast.Mod,
        ast.USub,
        ast.Eq,
        ast.NotEq,
        ast.Is,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.In,
        ast.NotIn,
        ast.And,
        ast.Or,
        ast.Not,
    }
)

ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "len",
        "max",
        "min",
        "range",
        "predicate",
        "ValueError",
    }
)

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset({"get"})

ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "xs",
        "state",
        "transition_count",
        "transitions",
        "sink_state_id",
        "accept_states",
        "x",
        "matched",
        "predicate",
        "target",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "abs": {1},
    "len": {1},
    "max": {2},
    "min": {2},
    "range": {1, 2, 3},
    "predicate": {1},
    "ValueError": {1},
}

METHOD_ARITIES: dict[str, set[int]] = {
    "get": {1, 2},
}

ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset({"int", "list", "None"})
