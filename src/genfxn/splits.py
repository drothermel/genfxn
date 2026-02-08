import random
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from genfxn.core.codegen import get_spec_value
from genfxn.core.models import Task


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


def _matches_holdout(task: Task, holdout: AxisHoldout) -> bool:
    """Check if task matches a single holdout condition."""
    value = get_spec_value(task.spec, holdout.axis_path)
    if value is None:
        return False

    match holdout.holdout_type:
        case HoldoutType.EXACT:
            return value == holdout.holdout_value
        case HoldoutType.RANGE:
            lo, hi = holdout.holdout_value
            if not isinstance(value, (int, float)):
                return False
            return lo <= value <= hi
        case HoldoutType.CONTAINS:
            try:
                return holdout.holdout_value in value
            except TypeError:
                return False
        case _:
            raise ValueError(f"Unknown holdout type: {holdout.holdout_type}")


def split_tasks(tasks: list[Task], holdouts: list[AxisHoldout]) -> SplitResult:
    """Split tasks: test = any holdout matches, train = no holdouts match."""
    train: list[Task] = []
    test: list[Task] = []
    for task in tasks:
        if any(_matches_holdout(task, h) for h in holdouts):
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
    """Randomly split tasks into train/test."""
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
