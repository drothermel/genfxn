from __future__ import annotations

from typing import Any, cast

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.verification.adapters.base import DefaultVerificationFamilyAdapter
from genfxn.verification.adapters.common import (
    DEFAULT_INT_RANGE,
    collect_int_constants,
    deterministic_rng,
    nonnegative_range,
    range_from_axes,
)
from genfxn.verification.adapters.families._shared import (
    choose_extra_int_edges,
    int_strategy,
    to_spec_dict,
)
from genfxn.verification.adapters.mutations import (
    candidate,
    finalize_candidates,
    i64_add,
    set_at_path,
)

FAMILY = "sequence_dp"


def _evaluate(spec_obj: Any, input_value: Any) -> Any:
    if not isinstance(input_value, dict):
        raise TypeError("sequence_dp input must be dict(a,b)")
    a = input_value.get("a")
    b = input_value.get("b")
    if not isinstance(a, list) or not isinstance(b, list):
        raise TypeError("sequence_dp input must include list a/b")
    return eval_sequence_dp(spec_obj, a, b)


def _layer2_strategy(
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    seed: int,
) -> SearchStrategy[Any]:
    value_range = range_from_axes(axes, "value_range", DEFAULT_INT_RANGE)
    len_a_range = nonnegative_range(
        range_from_axes(axes, "len_a_range", (0, 20))
    )
    len_b_range = nonnegative_range(
        range_from_axes(axes, "len_b_range", (0, 20))
    )
    lo, hi = value_range
    constants = collect_int_constants(to_spec_dict(spec_obj))

    rng = deterministic_rng(
        task_id,
        family=FAMILY,
        seed_value=seed,
        layer_name="layer2-strategy",
    )
    int_values = [lo, hi, 0, 1, -1]
    for constant in constants[:10]:
        int_values.extend([constant - 1, constant, constant + 1])
    int_values.extend(
        choose_extra_int_edges(
            lo=lo,
            hi=hi,
            constants=constants,
            rng=rng,
            count=48,
        )
    )
    int_value_strategy = int_strategy(lo=lo, hi=hi, edge_values=int_values)

    generated = st.fixed_dictionaries(
        {
            "a": st.lists(
                int_value_strategy,
                min_size=len_a_range[0],
                max_size=len_a_range[1],
            ),
            "b": st.lists(
                int_value_strategy,
                min_size=len_b_range[0],
                max_size=len_b_range[1],
            ),
        }
    )

    edge_cases = [
        {"a": [], "b": []},
        {"a": [0], "b": [0]},
        {"a": [1, -1], "b": [-1, 1]},
    ]

    return st.one_of(st.sampled_from(edge_cases), generated)


def _layer3_mutants(
    task_id: str,
    spec_obj: Any,  # noqa: ARG001
    spec_dict: dict[str, Any],
    budget: int,
    seed: int,
    mode: str,
) -> list[Any]:
    candidates: list[Any] = []

    template = spec_dict.get("template")
    if template == "global":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("template",), "local"),
                mutant_kind="sequence_dp_mode_mutation",
                rule_id="sequence_dp.template_global_to_local",
                metadata={"path": ["template"]},
            )
        )
    elif template == "local":
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("template",), "global"),
                mutant_kind="sequence_dp_mode_mutation",
                rule_id="sequence_dp.template_local_to_global",
                metadata={"path": ["template"]},
            )
        )

    output_mode = spec_dict.get("output_mode")
    output_alternates = {
        "score": "alignment_len",
        "alignment_len": "gap_count",
        "gap_count": "score",
    }
    alternate = output_alternates.get(output_mode)
    if alternate is not None:
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("output_mode",), alternate),
                mutant_kind="sequence_dp_mode_mutation",
                rule_id="sequence_dp.output_mode_swap",
                metadata={"path": ["output_mode"], "to": alternate},
            )
        )

    tie_break = spec_dict.get("step_tie_break")
    if isinstance(tie_break, str):
        other = (
            "left_up_diag" if tie_break != "left_up_diag" else "diag_up_left"
        )
        candidates.append(
            candidate(
                set_at_path(spec_dict, ("step_tie_break",), other),
                mutant_kind="sequence_dp_tiebreak_mutation",
                rule_id="sequence_dp.step_tie_break_swap",
                metadata={"path": ["step_tie_break"], "to": other},
            )
        )

    for field_name in ("match_score", "mismatch_score", "gap_score"):
        value = spec_dict.get(field_name)
        if type(value) is not int:
            continue
        for delta in (-1, 1):
            updated = i64_add(value, delta)
            if updated is None:
                continue
            candidates.append(
                candidate(
                    set_at_path(spec_dict, (field_name,), updated),
                    mutant_kind="sequence_dp_score_mutation",
                    rule_id=(
                        f"sequence_dp.{field_name}_"
                        f"{'minus' if delta < 0 else 'plus'}_one"
                    ),
                    metadata={"path": [field_name], "delta": delta},
                )
            )

    predicate = spec_dict.get("match_predicate")
    if isinstance(predicate, dict):
        kind = predicate.get("kind")
        if kind == "eq":
            mutated = dict(predicate)
            mutated["kind"] = "abs_diff_le"
            mutated["max_diff"] = 0
            candidates.append(
                candidate(
                    set_at_path(spec_dict, ("match_predicate",), mutated),
                    mutant_kind="sequence_dp_predicate_mutation",
                    rule_id="sequence_dp.predicate_eq_to_abs_diff_le",
                    metadata={"path": ["match_predicate", "kind"]},
                )
            )
        elif kind == "abs_diff_le":
            value = predicate.get("max_diff")
            if type(value) is int:
                if value > 0:
                    mutated = dict(predicate)
                    mutated["max_diff"] = value - 1
                    candidates.append(
                        candidate(
                            set_at_path(
                                spec_dict,
                                ("match_predicate",),
                                mutated,
                            ),
                            mutant_kind="sequence_dp_predicate_mutation",
                            rule_id="sequence_dp.max_diff_minus_one",
                            metadata={"path": ["match_predicate", "max_diff"]},
                        )
                    )
                mutated = dict(predicate)
                mutated["max_diff"] = value + 1
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("match_predicate",), mutated),
                        mutant_kind="sequence_dp_predicate_mutation",
                        rule_id="sequence_dp.max_diff_plus_one",
                        metadata={"path": ["match_predicate", "max_diff"]},
                    )
                )
        elif kind == "mod_eq":
            divisor = predicate.get("divisor")
            remainder = predicate.get("remainder")
            if type(divisor) is int and divisor > 1:
                mutated = dict(predicate)
                mutated["divisor"] = divisor - 1
                mutated["remainder"] = min(remainder or 0, divisor - 2)
                candidates.append(
                    candidate(
                        set_at_path(spec_dict, ("match_predicate",), mutated),
                        mutant_kind="sequence_dp_predicate_mutation",
                        rule_id="sequence_dp.divisor_minus_one",
                        metadata={"path": ["match_predicate", "divisor"]},
                    )
                )

    return finalize_candidates(
        candidates,
        validate_spec=lambda raw: validate_spec_for_family(FAMILY, raw),
        original_spec=spec_dict,
        task_id=task_id,
        family=FAMILY,
        seed=seed,
        mode=cast(Any, mode),
        budget=budget,
    )


ADAPTER = DefaultVerificationFamilyAdapter(
    family=FAMILY,
    evaluator=_evaluate,
    layer2_strategy_factory=_layer2_strategy,
    layer3_mutant_factory=_layer3_mutants,
)
