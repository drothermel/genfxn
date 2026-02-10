"""AST safety checks for graph_queries code validation."""

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
        ast.While,
        ast.Continue,
        ast.Expr,
        ast.BinOp,
        ast.BitAnd,
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
        ast.Set,
        ast.DictComp,
        ast.comprehension,
        ast.Subscript,
        ast.Attribute,
        ast.Break,
        ast.Load,
        ast.LShift,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.USub,
        ast.Eq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.And,
        ast.Or,
        ast.Not,
        ast.In,
        ast.Is,
        ast.IsNot,
    }
)

ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {
        "ValueError",
        "_wrap_i64",
        "dict",
        "len",
        "range",
    }
)

ALLOWED_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "add",
        "append",
        "get",
        "items",
        "pop",
        "sort",
        "values",
    }
)

ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "_",
        "_i64_mask",
        "_wrap_i64",
        "adjacency",
        "best",
        "best_cost_curr",
        "best_cost_prev",
        "best_cost",
        "best_idx",
        "best_node",
        "best_pair",
        "changed",
        "candidate_node",
        "candidate_pair",
        "cost",
        "directed",
        "edges",
        "frontier",
        "head",
        "hops",
        "i",
        "key",
        "n_nodes",
        "neighbor",
        "neighbors",
        "next_cost",
        "node",
        "prev",
        "query_type",
        "queue",
        "raw_u",
        "raw_v",
        "raw_w",
        "rev_key",
        "rev_prev",
        "u",
        "v",
        "value",
        "visited",
        "weight",
        "weighted",
        "wrapped",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "ValueError": {1},
    "_wrap_i64": {1},
    "dict": {1},
    "len": {1},
    "range": {1, 2, 3},
}

METHOD_ARITIES: dict[str, set[int]] = {
    "add": {1},
    "append": {1},
    "get": {1, 2},
    "items": {0},
    "pop": {0},
    "sort": {0},
    "values": {0},
}

ALLOWED_ANNOTATION_NAMES: frozenset[str] = frozenset(
    {
        "dict",
        "int",
        "list",
        "tuple",
    }
)
