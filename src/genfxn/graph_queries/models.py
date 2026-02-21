from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

_INT_RANGE_FIELDS = (
    "n_nodes_range",
    "edge_count_range",
    "weight_range",
)
INT32_MAX = (1 << 31) - 1
INT64_MAX = (1 << 63) - 1


def _validate_no_bool_int_range_bounds(data: Any) -> None:
    if not isinstance(data, dict):
        return

    for field_name in _INT_RANGE_FIELDS:
        value = data.get(field_name)
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            continue
        low, high = value
        if isinstance(low, bool) or isinstance(high, bool):
            raise ValueError(
                f"{field_name}: bool is not allowed for int range bounds"
            )


class GraphQueryType(str, Enum):
    REACHABLE = "reachable"
    MIN_HOPS = "min_hops"
    SHORTEST_PATH_COST = "shortest_path_cost"


class GraphEdge(BaseModel):
    u: int = Field(ge=0, le=INT32_MAX)
    v: int = Field(ge=0, le=INT32_MAX)
    w: int = Field(default=1, ge=0, le=INT64_MAX)

    @model_validator(mode="before")
    @classmethod
    def validate_input_edge(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        for field_name in ("u", "v", "w"):
            if isinstance(data.get(field_name), bool):
                raise ValueError(
                    f"{field_name}: bool is not allowed for int fields"
                )
        return data


class GraphQueriesSpec(BaseModel):
    query_type: GraphQueryType
    directed: bool
    weighted: bool
    n_nodes: int = Field(ge=1, le=INT32_MAX)
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def validate_input_spec(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if isinstance(data.get("n_nodes"), bool):
            raise ValueError("n_nodes: bool is not allowed for int fields")
        return data

    @model_validator(mode="after")
    def validate_spec(self) -> "GraphQueriesSpec":
        if self.n_nodes < 1:
            raise ValueError("n_nodes must be >= 1")
        if (
            self.query_type == GraphQueryType.SHORTEST_PATH_COST
            and not self.weighted
        ):
            raise ValueError("shortest_path_cost requires weighted=True")
        for edge in self.edges:
            if edge.w < 0:
                raise ValueError("edge.w must be >= 0")
            if edge.u < 0 or edge.u >= self.n_nodes:
                raise ValueError(
                    f"edge.u={edge.u} must be in [0, {self.n_nodes - 1}]"
                )
            if edge.v < 0 or edge.v >= self.n_nodes:
                raise ValueError(
                    f"edge.v={edge.v} must be in [0, {self.n_nodes - 1}]"
                )
        return self


class GraphQueriesAxes(BaseModel):
    target_difficulty: int | None = Field(default=None, ge=1, le=5)
    query_types: list[GraphQueryType] = Field(
        default_factory=lambda: list(GraphQueryType)
    )
    directed_choices: list[bool] = Field(default_factory=lambda: [False, True])
    weighted_choices: list[bool] = Field(default_factory=lambda: [False, True])
    n_nodes_range: tuple[int, int] = Field(default=(2, 8))
    edge_count_range: tuple[int, int] = Field(default=(1, 16))
    weight_range: tuple[int, int] = Field(default=(1, 9))
    disconnected_prob_range: tuple[float, float] = Field(default=(0.1, 0.4))
    multi_edge_prob_range: tuple[float, float] = Field(default=(0.0, 0.25))
    hub_bias_prob_range: tuple[float, float] = Field(default=(0.0, 0.4))

    @model_validator(mode="before")
    @classmethod
    def validate_input_axes(cls, data: Any) -> Any:
        _validate_no_bool_int_range_bounds(data)
        return data

    @model_validator(mode="after")
    def validate_axes(self) -> "GraphQueriesAxes":
        if not self.query_types:
            raise ValueError("query_types must not be empty")
        if not self.directed_choices:
            raise ValueError("directed_choices must not be empty")
        if not self.weighted_choices:
            raise ValueError("weighted_choices must not be empty")
        if (
            GraphQueryType.SHORTEST_PATH_COST in self.query_types
            and True not in self.weighted_choices
        ):
            raise ValueError("shortest_path_cost requires weighted=True")

        for name in (
            "n_nodes_range",
            "edge_count_range",
            "weight_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")

        if self.n_nodes_range[0] < 1:
            raise ValueError("n_nodes_range: low must be >= 1")
        if self.n_nodes_range[1] > INT32_MAX:
            raise ValueError(f"n_nodes_range: high must be <= {INT32_MAX}")
        if self.edge_count_range[0] < 0:
            raise ValueError("edge_count_range: low must be >= 0")
        if self.weight_range[0] < 0:
            raise ValueError("weight_range: low must be >= 0")
        if self.weight_range[1] > INT64_MAX:
            raise ValueError(f"weight_range: high must be <= {INT64_MAX}")

        for name in (
            "disconnected_prob_range",
            "multi_edge_prob_range",
            "hub_bias_prob_range",
        ):
            lo, hi = getattr(self, name)
            if lo > hi:
                raise ValueError(f"{name}: low ({lo}) must be <= high ({hi})")
            if lo < 0.0 or hi > 1.0:
                raise ValueError(f"{name}: values must be in [0.0, 1.0]")

        return self
