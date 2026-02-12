import math
import random
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from genfxn.core.codegen import get_spec_value, has_spec_value
from genfxn.core.models import Task, _freeze_query_value


class HoldoutType(str, Enum):
    EXACT = "exact"
    RANGE = "range"
    CONTAINS = "contains"


class AxisHoldout(BaseModel):
    axis_path: str = Field(description="Dot-separated path to spec value")
    holdout_type: HoldoutType = Field(
        description="How to match the holdout value"
    )
    holdout_value: Any = Field(description="Value to match against")


class SplitResult(BaseModel):
    train: list[Task] = Field(description="Tasks not matching any holdout")
    test: list[Task] = Field(description="Tasks matching at least one holdout")
    holdouts: list[AxisHoldout] = Field(description="Holdout conditions used")


def _is_non_bool_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_finite_non_bool_number(value: Any) -> bool:
    return _is_non_bool_number(value) and math.isfinite(value)


def _contains_non_finite_number(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, list | tuple | set | frozenset):
        return any(_contains_non_finite_number(item) for item in value)
    if isinstance(value, dict):
        return any(
            _contains_non_finite_number(key)
            or _contains_non_finite_number(item)
            for key, item in value.items()
        )
    return False


def _matches_exact_type_sensitive(value: Any, holdout_value: Any) -> bool:
    return _freeze_query_value(value) == _freeze_query_value(holdout_value)


def _contains_type_sensitive(value: Any, holdout_value: Any) -> bool:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return False
    holdout_key = _freeze_query_value(holdout_value)
    return any(
        _freeze_query_value(item) == holdout_key for item in value
    )


def matches_holdout(task: Task, holdout: AxisHoldout) -> bool:
    """Check if task matches a single holdout condition."""
    if not has_spec_value(task.spec, holdout.axis_path):
        return False
    value = get_spec_value(task.spec, holdout.axis_path)

    match holdout.holdout_type:
        case HoldoutType.EXACT:
            if _contains_non_finite_number(holdout.holdout_value):
                return False
            return _matches_exact_type_sensitive(
                value, holdout.holdout_value
            )
        case HoldoutType.RANGE:
            range_value = holdout.holdout_value
            if (
                not isinstance(range_value, tuple | list)
                or len(range_value) != 2
            ):
                return False
            lo, hi = range_value
            if (
                not _is_finite_non_bool_number(lo)
                or not _is_finite_non_bool_number(hi)
            ):
                return False
            if not _is_finite_non_bool_number(value):
                return False
            return lo <= value <= hi
        case HoldoutType.CONTAINS:
            if _contains_non_finite_number(holdout.holdout_value):
                return False
            return _contains_type_sensitive(value, holdout.holdout_value)
        case _:
            raise ValueError(f"Unknown holdout type: {holdout.holdout_type}")


def _matches_holdout(task: Task, holdout: AxisHoldout) -> bool:
    """Backward-compatible alias used by older tests/callers."""
    return matches_holdout(task, holdout)


def split_tasks(tasks: list[Task], holdouts: list[AxisHoldout]) -> SplitResult:
    """Split tasks: test = any holdout matches, train = no holdouts match."""
    train: list[Task] = []
    test: list[Task] = []
    for task in tasks:
        if any(matches_holdout(task, h) for h in holdouts):
            test.append(task)
        else:
            train.append(task)
    return SplitResult(train=train, test=test, holdouts=holdouts)


def random_split(
    tasks: list[Task],
    train_ratio: float,
    seed: int | None = None,
    *,
    in_place: bool = False,
) -> SplitResult:
    """Randomly split tasks into train/test.

    If in_place is True, the input list is shuffled in place.
    """
    if not (0.0 <= train_ratio <= 1.0):
        raise ValueError(
            f"train_ratio must be in [0.0, 1.0], got {train_ratio!r}"
        )
    rng = random.Random(seed)
    shuffled = tasks if in_place else tasks.copy()
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * train_ratio)
    return SplitResult(
        train=shuffled[:split_idx],
        test=shuffled[split_idx:],
        holdouts=[],
    )
