"""AST safety checks for stack_bytecode code validation."""

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
        ast.If,
        ast.While,
        ast.For,
        ast.Continue,
        ast.Break,
        ast.Expr,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Subscript,
        ast.Load,
        ast.Store,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
        ast.Mod,
        ast.BitXor,
        ast.USub,
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.In,
        ast.NotIn,
        ast.And,
        ast.Or,
    }
)

ALLOWED_CALL_NAMES: frozenset[str] = frozenset(
    {"abs", "len", "range", "repr", "str", "max", "min"}
)

ALLOWED_VAR_NAMES: frozenset[str] = frozenset(
    {
        "xs",
        "program",
        "max_step_count",
        "jump_target_mode",
        "input_mode",
        "stack",
        "pc",
        "steps",
        "n",
        "instr",
        "op",
        "a",
        "b",
        "idx",
        "target",
        "cond",
        "resolved",
        "sign",
    }
)

CALL_ARITIES: dict[str, set[int]] = {
    "abs": {1},
    "len": {1},
    "range": {1, 2, 3},
    "repr": {1},
    "str": {1},
    "max": {2},
    "min": {2},
}
