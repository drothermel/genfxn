from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field

from pydantic import BaseModel, ConfigDict

from genfxn.core.models import Task


class AxisGroup(BaseModel):
    """Valid axis value combinations for one primary-axis value."""

    model_config = ConfigDict(frozen=True)

    primary_value: str
    secondary_values: tuple[str, ...]
    tertiary_values: tuple[str, ...]


class CellSpace(BaseModel):
    """Declarative enumeration of valid strata cells for a family."""

    model_config = ConfigDict(frozen=True)

    family: str
    primary_axis: str
    groups: tuple[AxisGroup, ...]

    def valid_cells(self) -> list[str]:
        cells: list[str] = []
        for group in self.groups:
            for s in group.secondary_values:
                for t in group.tertiary_values:
                    cells.append(f"{group.primary_value}|{s}|{t}")
        return cells


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

_STATEFUL_CELL_SPACE = CellSpace(
    family="stateful",
    primary_axis="template",
    groups=(
        AxisGroup(
            primary_value="conditional_linear_sum",
            secondary_values=_PREDICATE_CLASSES,
            tertiary_values=_TRANSFORM_COMPLEXITIES,
        ),
        AxisGroup(
            primary_value="resetting_best_prefix_sum",
            secondary_values=_PREDICATE_CLASSES,
            tertiary_values=_TRANSFORM_COMPLEXITIES,
        ),
        AxisGroup(
            primary_value="longest_run",
            secondary_values=("comparison", "modular"),
            tertiary_values=("low",),
        ),
    ),
)

_SIMPLE_ALGORITHMS_CELL_SPACE = CellSpace(
    family="simple_algorithms",
    primary_axis="template",
    groups=(
        AxisGroup(
            primary_value="most_frequent",
            secondary_values=_MOST_FREQUENT_TIE_BREAKS,
            tertiary_values=_PREPROCESS_BUCKETS,
        ),
        AxisGroup(
            primary_value="count_pairs_sum",
            secondary_values=_COUNT_PAIRS_MODES,
            tertiary_values=_PREPROCESS_BUCKETS,
        ),
        AxisGroup(
            primary_value="max_window_sum",
            secondary_values=_K_BUCKETS,
            tertiary_values=_PREPROCESS_BUCKETS,
        ),
    ),
)

_FSM_CELL_SPACE = CellSpace(
    family="fsm",
    primary_axis="output_mode",
    groups=(
        AxisGroup(
            primary_value="final_state_id",
            secondary_values=_FSM_UNDEFINED_POLICIES,
            tertiary_values=_N_STATES_BUCKETS,
        ),
        AxisGroup(
            primary_value="accept_bool",
            secondary_values=_FSM_UNDEFINED_POLICIES,
            tertiary_values=_N_STATES_BUCKETS,
        ),
        AxisGroup(
            primary_value="transition_count",
            secondary_values=_FSM_UNDEFINED_POLICIES,
            tertiary_values=_N_STATES_BUCKETS,
        ),
    ),
)

_BITOPS_CELL_SPACE = CellSpace(
    family="bitops",
    primary_axis="width_bits",
    groups=(
        AxisGroup(
            primary_value="8",
            secondary_values=_N_OPS_BUCKETS,
            tertiary_values=_BIT_OP_MIX_BUCKETS,
        ),
        AxisGroup(
            primary_value="16",
            secondary_values=_N_OPS_BUCKETS,
            tertiary_values=_BIT_OP_MIX_BUCKETS,
        ),
        AxisGroup(
            primary_value="32",
            secondary_values=_N_OPS_BUCKETS,
            tertiary_values=_BIT_OP_MIX_BUCKETS,
        ),
    ),
)


@dataclass(frozen=True)
class StrataPlan:
    family: str
    primary_axis: str
    target_counts: dict[str, int]
    core_target_counts: dict[str, int]
    repair_budget: int
    target_total: int
    cell_space: CellSpace | None = dc_field(default=None)

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

    cells = _STATEFUL_CELL_SPACE.valid_cells()
    # 20 cells * 15 = 300 exactly, no repair cells needed.
    core, target = _apply_repairs(
        cells=cells,
        base_count=15,
        repair_cells=[],
    )
    return StrataPlan(
        family="stateful",
        primary_axis="template",
        target_counts=target,
        core_target_counts=core,
        repair_budget=0,
        target_total=total,
        cell_space=_STATEFUL_CELL_SPACE,
    )


def _simple_algorithms_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError(
            "simple_algorithms IRT stratification is locked to 300 items/family"
        )

    target_counts: dict[str, int] = {}
    core_counts: dict[str, int] = {}

    _group_configs: list[tuple[str, int, list[str]]] = [
        (
            "most_frequent",
            16,
            [
                "most_frequent|smallest|none",
                "most_frequent|smallest|both",
                "most_frequent|first_seen|none",
                "most_frequent|first_seen|both",
            ],
        ),
        (
            "count_pairs_sum",
            16,
            [
                "count_pairs_sum|all_indices|none",
                "count_pairs_sum|all_indices|both",
                "count_pairs_sum|unique_values|none",
                "count_pairs_sum|unique_values|both",
            ],
        ),
        (
            "max_window_sum",
            11,
            ["max_window_sum|medium|single"],
        ),
    ]

    for group in _SIMPLE_ALGORITHMS_CELL_SPACE.groups:
        template = group.primary_value
        cells = [
            f"{template}|{s}|{t}"
            for s in group.secondary_values
            for t in group.tertiary_values
        ]
        base_count, repair_cells = next(
            (bc, rc) for name, bc, rc in _group_configs if name == template
        )
        g_core, g_target = _apply_repairs(
            cells=cells,
            base_count=base_count,
            repair_cells=repair_cells,
        )
        target_counts.update(g_target)
        core_counts.update(g_core)

    if sum(target_counts.values()) != total:
        raise ValueError("simple_algorithms target counts do not sum to 300")

    return StrataPlan(
        family="simple_algorithms",
        primary_axis="template",
        target_counts=target_counts,
        core_target_counts=core_counts,
        repair_budget=9,
        target_total=total,
        cell_space=_SIMPLE_ALGORITHMS_CELL_SPACE,
    )


def _fsm_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError("fsm IRT stratification is locked to 300 items/family")

    cells = _FSM_CELL_SPACE.valid_cells()
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
        cell_space=_FSM_CELL_SPACE,
    )


def _bitops_plan(total: int) -> StrataPlan:
    if total != _LOCKED_PER_FAMILY_TOTAL:
        raise ValueError(
            "bitops IRT stratification is locked to 300 items/family"
        )

    cells = _BITOPS_CELL_SPACE.valid_cells()
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
        cell_space=_BITOPS_CELL_SPACE,
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
