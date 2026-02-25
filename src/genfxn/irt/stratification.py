from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from genfxn.core.models import Task

_LOCKED_PER_FAMILY_TOTAL = 300

_STATEFUL_TEMPLATES = (
    "conditional_linear_sum",
    "resetting_best_prefix_sum",
    "longest_run",
)
_PREDICATE_CLASSES = ("parity", "comparison", "modular")
_TRANSFORM_COMPLEXITIES = ("low", "mixed", "high")

_MOST_FREQUENT_TIE_BREAKS = ("smallest", "first_seen")
_COUNT_PAIRS_MODES = ("all_indices", "unique_values")
_PREPROCESS_BUCKETS = ("none", "single", "both")
_K_BUCKETS = ("small", "medium", "large")

_FSM_OUTPUT_MODES = ("final_state_id", "accept_bool", "transition_count")
_FSM_UNDEFINED_POLICIES = ("sink", "stay", "error")
_N_STATES_BUCKETS = ("small", "medium", "large")

_BIT_WIDTH_BITS = ("8", "16", "32")
_N_OPS_BUCKETS = ("short", "medium", "long")
_BIT_OP_MIX_BUCKETS = ("logic_only", "shift_mix", "advanced")


@dataclass(frozen=True)
class StrataPlan:
    family: str
    primary_axis: str
    target_counts: dict[str, int]
    core_target_counts: dict[str, int]
    repair_budget: int
    target_total: int

    def classify(self, task: Task) -> tuple[str, dict[str, str]]:
        if self.family == "stateful":
            fields = _stateful_fields(task)
            return _stateful_cell(fields), fields
        if self.family == "simple_algorithms":
            fields = _simple_algorithms_fields(task)
            return _simple_algorithms_cell(fields), fields
        if self.family == "fsm":
            fields = _fsm_fields(task)
            return _fsm_cell(fields), fields
        if self.family == "bitops":
            fields = _bitops_fields(task)
            return _bitops_cell(fields), fields
        raise ValueError(f"unsupported family for strata plan: {self.family}")


def _predicate_class_from_kind(kind: str) -> str:
    if kind in {"even", "odd"}:
        return "parity"
    if kind in {"lt", "le", "gt", "ge"}:
        return "comparison"
    if kind == "mod_eq":
        return "modular"
    return "comparison"


def _transform_complexity_from_kinds(kinds: list[str]) -> str:
    if not kinds:
        return "low"
    if any(kind == "scale" for kind in kinds):
        return "high"
    if any(kind in {"abs", "shift"} for kind in kinds):
        return "mixed"
    if all(kind in {"identity", "negate"} for kind in kinds):
        return "low"
    return "mixed"


def _stateful_fields(task: Task) -> dict[str, str]:
    spec = task.spec
    template = str(spec.get("template", "conditional_linear_sum"))
    if template not in _STATEFUL_TEMPLATES:
        # Explicitly exclude older stateful templates from IRT calibration.
        raise ValueError("unsupported stateful template for IRT bank")

    if template == "conditional_linear_sum":
        pred_kind = str(spec.get("predicate", {}).get("kind", "lt"))
        transforms = [
            str(spec.get("true_transform", {}).get("kind", "identity")),
            str(spec.get("false_transform", {}).get("kind", "identity")),
        ]
    elif template == "resetting_best_prefix_sum":
        pred_kind = str(spec.get("reset_predicate", {}).get("kind", "lt"))
        value_transform = spec.get("value_transform")
        transforms = []
        if isinstance(value_transform, dict):
            transforms.append(str(value_transform.get("kind", "identity")))
    else:
        pred_kind = str(spec.get("match_predicate", {}).get("kind", "lt"))
        transforms = []

    return {
        "template": template,
        "predicate_class": _predicate_class_from_kind(pred_kind),
        "transform_complexity": _transform_complexity_from_kinds(transforms),
    }


def _simple_algorithms_fields(task: Task) -> dict[str, str]:
    spec = task.spec
    template = str(spec.get("template", "most_frequent"))
    pre_filter = spec.get("pre_filter")
    pre_transform = spec.get("pre_transform")
    if pre_filter is None and pre_transform is None:
        preprocess_bucket = "none"
    elif pre_filter is not None and pre_transform is not None:
        preprocess_bucket = "both"
    else:
        preprocess_bucket = "single"

    fields: dict[str, str] = {
        "template": template,
        "preprocess_bucket": preprocess_bucket,
    }
    if template == "most_frequent":
        fields["tie_break"] = str(spec.get("tie_break", "smallest"))
    elif template == "count_pairs_sum":
        fields["counting_mode"] = str(spec.get("counting_mode", "all_indices"))
    elif template == "max_window_sum":
        k = int(spec.get("k", 1))
        if k <= 3:
            fields["k_bucket"] = "small"
        elif k <= 6:
            fields["k_bucket"] = "medium"
        else:
            fields["k_bucket"] = "large"
    else:
        raise ValueError("unsupported simple_algorithms template")
    return fields


def _fsm_fields(task: Task) -> dict[str, str]:
    spec = task.spec
    n_states = len(spec.get("states", []))
    if n_states <= 3:
        n_states_bucket = "small"
    elif n_states == 4:
        n_states_bucket = "medium"
    else:
        n_states_bucket = "large"

    return {
        "output_mode": str(spec.get("output_mode", "final_state_id")),
        "undefined_transition_policy": str(
            spec.get("undefined_transition_policy", "sink")
        ),
        "n_states_bucket": n_states_bucket,
        "machine_type": str(spec.get("machine_type", "moore")),
    }


def _bitops_fields(task: Task) -> dict[str, str]:
    spec = task.spec
    width_bits = int(spec.get("width_bits", 8))
    width_bucket = "32"
    if width_bits <= 8:
        width_bucket = "8"
    elif width_bits <= 16:
        width_bucket = "16"

    operations = spec.get("operations", [])
    n_ops = len(operations)
    if n_ops <= 3:
        n_ops_bucket = "short"
    elif n_ops == 4:
        n_ops_bucket = "medium"
    else:
        n_ops_bucket = "long"

    op_names = {
        str(op.get("op"))
        for op in operations
        if isinstance(op, dict) and "op" in op
    }
    advanced_ops = {"popcount", "parity"}
    logic_ops = {"and_mask", "or_mask", "xor_mask", "not"}
    shift_ops = {"shl", "shr_logical", "rotl", "rotr"}

    if op_names & advanced_ops:
        op_mix_bucket = "advanced"
    elif op_names and op_names.issubset(logic_ops):
        op_mix_bucket = "logic_only"
    elif (op_names & shift_ops) and not (op_names & advanced_ops):
        op_mix_bucket = "shift_mix"
    else:
        op_mix_bucket = "shift_mix"

    return {
        "width_bits": width_bucket,
        "n_ops_bucket": n_ops_bucket,
        "op_mix_bucket": op_mix_bucket,
    }


def _stateful_cell(fields: dict[str, str]) -> str:
    return (
        f"{fields['template']}|{fields['predicate_class']}|"
        f"{fields['transform_complexity']}"
    )


def _simple_algorithms_cell(fields: dict[str, str]) -> str:
    template = fields["template"]
    if template == "most_frequent":
        return f"{template}|{fields['tie_break']}|{fields['preprocess_bucket']}"
    if template == "count_pairs_sum":
        return (
            f"{template}|{fields['counting_mode']}|"
            f"{fields['preprocess_bucket']}"
        )
    return f"{template}|{fields['k_bucket']}|{fields['preprocess_bucket']}"


def _fsm_cell(fields: dict[str, str]) -> str:
    return (
        f"{fields['output_mode']}|{fields['undefined_transition_policy']}|"
        f"{fields['n_states_bucket']}"
    )


def _bitops_cell(fields: dict[str, str]) -> str:
    return (
        f"{fields['width_bits']}|{fields['n_ops_bucket']}|"
        f"{fields['op_mix_bucket']}"
    )


def _apply_repairs(
    *,
    cells: list[str],
    base_count: int,
    repair_cells: list[str],
) -> tuple[dict[str, int], dict[str, int]]:
    core = {cell: base_count for cell in cells}
    target = dict(core)
    for cell in repair_cells:
        if cell not in target:
            raise ValueError(f"repair cell {cell!r} is not in strata cells")
        target[cell] += 1
    return core, target


def _stateful_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError(
            "stateful IRT stratification is locked to 300 items/family"
        )

    cells = [
        f"{template}|{predicate_class}|{complexity}"
        for template, predicate_class, complexity in product(
            _STATEFUL_TEMPLATES,
            _PREDICATE_CLASSES,
            _TRANSFORM_COMPLEXITIES,
        )
    ]
    repair_cells = [
        f"{template}|parity|low" for template in _STATEFUL_TEMPLATES
    ]
    core, target = _apply_repairs(
        cells=cells,
        base_count=11,
        repair_cells=repair_cells,
    )
    return StrataPlan(
        family="stateful",
        primary_axis="template",
        target_counts=target,
        core_target_counts=core,
        repair_budget=3,
        target_total=total,
    )


def _simple_algorithms_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError(
            "simple_algorithms IRT stratification is locked to 300 items/family"
        )

    target_counts: dict[str, int] = {}
    core_counts: dict[str, int] = {}

    most_frequent_cells = [
        f"most_frequent|{tie_break}|{preprocess}"
        for tie_break, preprocess in product(
            _MOST_FREQUENT_TIE_BREAKS,
            _PREPROCESS_BUCKETS,
        )
    ]
    mf_core, mf_target = _apply_repairs(
        cells=most_frequent_cells,
        base_count=16,
        repair_cells=[
            "most_frequent|smallest|none",
            "most_frequent|smallest|both",
            "most_frequent|first_seen|none",
            "most_frequent|first_seen|both",
        ],
    )
    target_counts.update(mf_target)
    core_counts.update(mf_core)

    count_pairs_cells = [
        f"count_pairs_sum|{mode}|{preprocess}"
        for mode, preprocess in product(
            _COUNT_PAIRS_MODES,
            _PREPROCESS_BUCKETS,
        )
    ]
    cp_core, cp_target = _apply_repairs(
        cells=count_pairs_cells,
        base_count=16,
        repair_cells=[
            "count_pairs_sum|all_indices|none",
            "count_pairs_sum|all_indices|both",
            "count_pairs_sum|unique_values|none",
            "count_pairs_sum|unique_values|both",
        ],
    )
    target_counts.update(cp_target)
    core_counts.update(cp_core)

    max_window_cells = [
        f"max_window_sum|{k_bucket}|{preprocess}"
        for k_bucket, preprocess in product(_K_BUCKETS, _PREPROCESS_BUCKETS)
    ]
    mw_core, mw_target = _apply_repairs(
        cells=max_window_cells,
        base_count=11,
        repair_cells=["max_window_sum|medium|single"],
    )
    target_counts.update(mw_target)
    core_counts.update(mw_core)

    if sum(target_counts.values()) != total:
        raise ValueError("simple_algorithms target counts do not sum to 300")

    return StrataPlan(
        family="simple_algorithms",
        primary_axis="template",
        target_counts=target_counts,
        core_target_counts=core_counts,
        repair_budget=9,
        target_total=total,
    )


def _fsm_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError("fsm IRT stratification is locked to 300 items/family")

    cells = [
        f"{output_mode}|{policy}|{n_states_bucket}"
        for output_mode, policy, n_states_bucket in product(
            _FSM_OUTPUT_MODES,
            _FSM_UNDEFINED_POLICIES,
            _N_STATES_BUCKETS,
        )
    ]
    repair_cells = [
        f"{output_mode}|sink|small" for output_mode in _FSM_OUTPUT_MODES
    ]
    core, target = _apply_repairs(
        cells=cells,
        base_count=11,
        repair_cells=repair_cells,
    )
    return StrataPlan(
        family="fsm",
        primary_axis="output_mode",
        target_counts=target,
        core_target_counts=core,
        repair_budget=3,
        target_total=total,
    )


def _bitops_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError(
            "bitops IRT stratification is locked to 300 items/family"
        )

    cells = [
        f"{width_bits}|{n_ops}|{op_mix}"
        for width_bits, n_ops, op_mix in product(
            _BIT_WIDTH_BITS,
            _N_OPS_BUCKETS,
            _BIT_OP_MIX_BUCKETS,
        )
    ]
    repair_cells = [
        f"{width_bits}|short|logic_only" for width_bits in _BIT_WIDTH_BITS
    ]
    core, target = _apply_repairs(
        cells=cells,
        base_count=11,
        repair_cells=repair_cells,
    )
    return StrataPlan(
        family="bitops",
        primary_axis="width_bits",
        target_counts=target,
        core_target_counts=core,
        repair_budget=3,
        target_total=total,
    )


def get_strata_plan(family: str, total: int) -> StrataPlan:
    if family == "stateful":
        return _stateful_plan(total)
    if family == "simple_algorithms":
        return _simple_algorithms_plan(total)
    if family == "fsm":
        return _fsm_plan(total)
    if family == "bitops":
        return _bitops_plan(total)
    raise ValueError(f"unsupported family for IRT calibration bank: {family}")


def primary_axis_value(plan: StrataPlan, fields: dict[str, str]) -> str:
    return fields[plan.primary_axis]


def cell_distance(left: dict[str, str], right: dict[str, str]) -> int:
    keys = sorted(set(left) | set(right))
    return sum(1 for key in keys if left.get(key) != right.get(key))


def parse_cell_fields(family: str, cell: str) -> dict[str, str]:
    parts = cell.split("|")
    if family == "stateful":
        if len(parts) != 3:
            raise ValueError(f"invalid stateful cell: {cell!r}")
        return {
            "template": parts[0],
            "predicate_class": parts[1],
            "transform_complexity": parts[2],
        }
    if family == "simple_algorithms":
        if len(parts) != 3:
            raise ValueError(f"invalid simple_algorithms cell: {cell!r}")
        template = parts[0]
        if template == "most_frequent":
            return {
                "template": template,
                "tie_break": parts[1],
                "preprocess_bucket": parts[2],
            }
        if template == "count_pairs_sum":
            return {
                "template": template,
                "counting_mode": parts[1],
                "preprocess_bucket": parts[2],
            }
        if template == "max_window_sum":
            return {
                "template": template,
                "k_bucket": parts[1],
                "preprocess_bucket": parts[2],
            }
        raise ValueError(
            f"unsupported simple_algorithms template cell: {cell!r}"
        )
    if family == "fsm":
        if len(parts) != 3:
            raise ValueError(f"invalid fsm cell: {cell!r}")
        return {
            "output_mode": parts[0],
            "undefined_transition_policy": parts[1],
            "n_states_bucket": parts[2],
        }
    if family == "bitops":
        if len(parts) != 3:
            raise ValueError(f"invalid bitops cell: {cell!r}")
        return {
            "width_bits": parts[0],
            "n_ops_bucket": parts[1],
            "op_mix_bucket": parts[2],
        }
    raise ValueError(f"unsupported family: {family}")
