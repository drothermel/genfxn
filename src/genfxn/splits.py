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
            return lo <= value <= hi
        case HoldoutType.CONTAINS:
            return holdout.holdout_value in value


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
