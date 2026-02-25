from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VerificationLayer(str, Enum):
    LAYER1_SPEC_BOUNDARY = "layer1_spec_boundary"
    LAYER2_PROPERTY = "layer2_property"
    LAYER3_MUTATION = "layer3_mutation"


def normalize_case_value(value: Any) -> Any:
    """Normalize values so case payloads are JSON-roundtrip stable."""
    if isinstance(value, Enum):
        return normalize_case_value(value.value)
    if isinstance(value, dict):
        return {key: normalize_case_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [normalize_case_value(item) for item in value]
    if isinstance(value, set | frozenset):
        normalized_items = [normalize_case_value(item) for item in value]
        return sorted(normalized_items, key=repr)
    return value


class VerificationCase(BaseModel):
    task_id: str
    family: str
    layer: VerificationLayer
    case_id: str
    input: Any
    expected_output: Any
    seed: int | None = None
    source_detail: dict[str, Any] = Field(default_factory=dict)

    @field_validator("input", "expected_output", mode="before")
    @classmethod
    def _normalize_case_fields(cls, value: Any) -> Any:
        return normalize_case_value(value)

    @field_validator("source_detail", mode="before")
    @classmethod
    def _normalize_source_detail(cls, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            return {"value": normalize_case_value(value)}
        return {
            str(key): normalize_case_value(item) for key, item in value.items()
        }


class MutationCurvePoint(BaseModel):
    n_tests: int
    mutation_score: float


class VerificationMetrics(BaseModel):
    task_id: str
    family: str
    n_layer1_cases: int
    n_layer2_cases: int
    n_layer3_cases: int
    mutation_score: float
    mutation_score_curve: list[MutationCurvePoint]
    heldout_mutant_escape_rate: float
    heldout_mutant_escape_ci95: float


class VerificationFailure(BaseModel):
    task_id: str
    family: str
    case_id: str
    message: str
