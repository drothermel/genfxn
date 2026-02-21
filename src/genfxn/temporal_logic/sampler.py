import random
from typing import Any

from genfxn.core.trace import TraceStep, trace_step
from genfxn.temporal_logic.models import (
    PredicateKind,
    TemporalLogicAxes,
    TemporalLogicSpec,
    TemporalOperator,
)

_UNARY_OPERATORS = frozenset(
    {
        TemporalOperator.NOT,
        TemporalOperator.NEXT,
        TemporalOperator.EVENTUALLY,
        TemporalOperator.ALWAYS,
    }
)
_BINARY_OPERATORS = frozenset(
    {
        TemporalOperator.AND,
        TemporalOperator.OR,
        TemporalOperator.UNTIL,
        TemporalOperator.SINCE,
    }
)


def _sample_int_in_range(
    value_range: tuple[int, int],
    rng: random.Random,
) -> int:
    return rng.randint(value_range[0], value_range[1])


def _sample_operator_candidates(
    operator_mix: list[TemporalOperator],
    include_since: bool,
) -> tuple[list[TemporalOperator], list[TemporalOperator]]:
    available = list(dict.fromkeys(operator_mix))
    if not include_since:
        available = [op for op in available if op != TemporalOperator.SINCE]
    if not available:
        available = [TemporalOperator.ATOM]

    non_atom = [op for op in available if op != TemporalOperator.ATOM]
    return available, non_atom


def _sample_formula(
    *,
    depth: int,
    operator_mix: list[TemporalOperator],
    include_since: bool,
    predicate_constant_range: tuple[int, int],
    rng: random.Random,
) -> dict[str, Any]:
    available, non_atom = _sample_operator_candidates(
        operator_mix, include_since
    )
    if depth <= 1 or not non_atom:
        predicate = rng.choice(list(PredicateKind))
        constant = _sample_int_in_range(predicate_constant_range, rng)
        return {
            "op": TemporalOperator.ATOM.value,
            "predicate": predicate.value,
            "constant": constant,
        }

    chosen = rng.choice(non_atom)
    if chosen in _UNARY_OPERATORS:
        child = _sample_formula(
            depth=depth - 1,
            operator_mix=available,
            include_since=include_since,
            predicate_constant_range=predicate_constant_range,
            rng=rng,
        )
        return {"op": chosen.value, "child": child}

    if chosen in _BINARY_OPERATORS:
        # Preserve requested depth by forcing one branch to depth-1.
        force_left = bool(rng.randint(0, 1))
        if force_left:
            left_depth = depth - 1
            right_depth = rng.randint(1, depth - 1)
        else:
            left_depth = rng.randint(1, depth - 1)
            right_depth = depth - 1
        left = _sample_formula(
            depth=left_depth,
            operator_mix=available,
            include_since=include_since,
            predicate_constant_range=predicate_constant_range,
            rng=rng,
        )
        right = _sample_formula(
            depth=right_depth,
            operator_mix=available,
            include_since=include_since,
            predicate_constant_range=predicate_constant_range,
            rng=rng,
        )
        return {"op": chosen.value, "left": left, "right": right}

    raise ValueError(f"Unsupported operator for sampling: {chosen.value}")


def sample_temporal_logic_spec(
    axes: TemporalLogicAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> TemporalLogicSpec:
    if rng is None:
        rng = random.Random()  # noqa: S311

    output_mode = rng.choice(axes.output_modes)
    include_since = rng.choice(axes.include_since_choices)
    depth = _sample_int_in_range(axes.formula_depth_range, rng)

    formula = _sample_formula(
        depth=depth,
        operator_mix=axes.operator_mix,
        include_since=include_since,
        predicate_constant_range=axes.predicate_constant_range,
        rng=rng,
    )

    trace_step(
        trace,
        "sample_output_mode",
        f"Output mode: {output_mode.value}",
        output_mode.value,
    )
    trace_step(
        trace,
        "sample_formula_depth",
        f"Formula depth: {depth}",
        depth,
    )
    trace_step(
        trace,
        "sample_include_since",
        f"Include SINCE: {include_since}",
        include_since,
    )
    trace_step(
        trace,
        "sample_formula",
        "Sampled temporal formula AST",
        formula,
    )

    return TemporalLogicSpec(
        output_mode=output_mode,
        formula=formula,
    )
