from __future__ import annotations

import hashlib
import random
import string
from typing import Any

from hypothesis import strategies as st

from genfxn.bitops.eval import eval_bitops
from genfxn.core.spec_registry import validate_spec_for_family
from genfxn.fsm.eval import eval_fsm
from genfxn.graph_queries.eval import eval_graph_queries
from genfxn.intervals.eval import eval_intervals
from genfxn.piecewise.eval import eval_piecewise
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.simple_algorithms.eval import eval_simple_algorithms
from genfxn.stack_bytecode.eval import eval_stack_bytecode
from genfxn.stateful.eval import eval_stateful
from genfxn.stringrules.eval import eval_stringrules
from genfxn.temporal_logic.eval import eval_temporal_logic

_DEFAULT_INT_RANGE = (-100, 100)
_DEFAULT_LIST_LENGTH_RANGE = (0, 20)


def _seed_for_task_layer(task_id: str, layer_name: str, seed: int = 0) -> int:
    digest = hashlib.sha256(f"{task_id}:{layer_name}:{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _collect_int_constants(value: Any) -> list[int]:
    constants: list[int] = []

    def _visit(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int):
            constants.append(node)
            return
        if isinstance(node, list | tuple | set | frozenset):
            for child in node:
                _visit(child)
            return
        if isinstance(node, dict):
            for child in node.values():
                _visit(child)

    _visit(value)
    return sorted(set(constants))


def _range_from_axes(
    axes: dict[str, Any] | None,
    key: str,
    default: tuple[int, int],
) -> tuple[int, int]:
    if axes is None:
        return default
    value = axes.get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default
    lo, hi = value
    if isinstance(lo, bool) or isinstance(hi, bool):
        return default
    if not isinstance(lo, int) or not isinstance(hi, int):
        return default
    if lo > hi:
        return default
    return lo, hi


def _random_string(rng: random.Random, lo: int, hi: int) -> str:
    alphabet = string.ascii_letters + string.digits + " _-"
    n = rng.randint(max(0, lo), max(0, hi))
    return "".join(rng.choice(alphabet) for _ in range(n))


def _sample_int_lists(
    *,
    count: int,
    rng: random.Random,
    value_range: tuple[int, int],
    length_range: tuple[int, int],
    constants: list[int],
) -> list[list[int]]:
    lo, hi = value_range
    len_lo, len_hi = length_range

    candidates: list[list[int]] = [[], [lo], [hi], [0], [1, -1], [lo, hi]]
    for c in constants[:10]:
        candidates.extend([[c], [c - 1, c, c + 1]])

    while len(candidates) < count:
        length = rng.randint(len_lo, len_hi)
        if rng.random() < 0.65 and constants:
            values = [rng.choice(constants) for _ in range(length)]
        else:
            values = [rng.randint(lo, hi) for _ in range(length)]
        candidates.append(values)

    return candidates[:count]


def _sample_string_inputs(
    *,
    count: int,
    rng: random.Random,
    length_range: tuple[int, int],
) -> list[str]:
    lo, hi = length_range
    candidates = ["", "a", "A", "0", "abc", "ABC", "a1B2", "  spaced  "]
    while len(candidates) < count:
        candidates.append(_random_string(rng, lo, hi))
    return candidates[:count]


def _sample_intervals_inputs(
    *,
    count: int,
    rng: random.Random,
    endpoint_range: tuple[int, int],
    list_length_range: tuple[int, int],
    constants: list[int],
) -> list[list[tuple[int, int]]]:
    lo, hi = endpoint_range
    len_lo, len_hi = list_length_range
    candidates: list[list[tuple[int, int]]] = [
        [],
        [(0, 0)],
        [(0, 1)],
        [(1, 0)],
        [(lo, hi)],
        [(hi, lo)],
    ]
    if constants:
        c = constants[0]
        candidates.append([(c - 1, c), (c, c + 1)])

    while len(candidates) < count:
        n = rng.randint(len_lo, len_hi)
        sample: list[tuple[int, int]] = []
        for _ in range(n):
            a = rng.randint(lo, hi)
            b = rng.randint(lo, hi)
            sample.append((a, b))
        candidates.append(sample)

    return candidates[:count]


def _sample_sequence_dp_inputs(
    *,
    count: int,
    rng: random.Random,
    value_range: tuple[int, int],
    len_a_range: tuple[int, int],
    len_b_range: tuple[int, int],
    constants: list[int],
) -> list[dict[str, list[int]]]:
    lo, hi = value_range
    a_lo, a_hi = len_a_range
    b_lo, b_hi = len_b_range

    candidates: list[dict[str, list[int]]] = [
        {"a": [], "b": []},
        {"a": [0], "b": [0]},
        {"a": [1, -1], "b": [-1, 1]},
    ]

    while len(candidates) < count:
        len_a = rng.randint(a_lo, a_hi)
        len_b = rng.randint(b_lo, b_hi)
        if rng.random() < 0.65 and constants:
            a = [rng.choice(constants) for _ in range(len_a)]
            b = [rng.choice(constants) for _ in range(len_b)]
        else:
            a = [rng.randint(lo, hi) for _ in range(len_a)]
            b = [rng.randint(lo, hi) for _ in range(len_b)]
        candidates.append({"a": a, "b": b})

    return candidates[:count]


def _sample_graph_query_inputs(
    *,
    count: int,
    rng: random.Random,
    n_nodes: int,
) -> list[dict[str, int]]:
    if n_nodes <= 0:
        return [{"src": 0, "dst": 0} for _ in range(count)]

    candidates: list[dict[str, int]] = [
        {"src": 0, "dst": 0},
        {"src": 0, "dst": n_nodes - 1},
        {"src": n_nodes - 1, "dst": 0},
        {"src": n_nodes - 1, "dst": n_nodes - 1},
    ]

    while len(candidates) < count:
        candidates.append(
            {
                "src": rng.randrange(n_nodes),
                "dst": rng.randrange(n_nodes),
            }
        )

    return candidates[:count]


def hypothesis_strategy_for_family(
    family: str,
    *,
    axes: dict[str, Any] | None,
    spec_obj: Any,
) -> st.SearchStrategy[Any]:
    constants = _collect_int_constants(spec_obj.model_dump(mode="python"))

    if family in {"piecewise", "bitops"}:
        lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        base = st.integers(min_value=lo, max_value=hi)
        if constants:
            return st.one_of(st.sampled_from(constants[:16]), base)
        return base

    if family in {
        "stateful",
        "simple_algorithms",
        "stack_bytecode",
        "fsm",
        "temporal_logic",
    }:
        lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        len_lo, len_hi = _range_from_axes(
            axes,
            "list_length_range",
            _DEFAULT_LIST_LENGTH_RANGE,
        )
        atom = st.integers(min_value=lo, max_value=hi)
        if constants:
            atom = st.one_of(st.sampled_from(constants[:16]), atom)
        return st.lists(atom, min_size=len_lo, max_size=len_hi)

    if family == "stringrules":
        len_lo, len_hi = _range_from_axes(axes, "string_length_range", (0, 20))
        alphabet = string.ascii_letters + string.digits + " _-"
        return st.text(alphabet=alphabet, min_size=len_lo, max_size=len_hi)

    if family == "intervals":
        lo, hi = _range_from_axes(axes, "endpoint_range", _DEFAULT_INT_RANGE)
        len_lo, len_hi = _range_from_axes(axes, "n_intervals_range", (0, 10))
        interval = st.tuples(
            st.integers(min_value=lo, max_value=hi),
            st.integers(min_value=lo, max_value=hi),
        )
        return st.lists(interval, min_size=len_lo, max_size=len_hi)

    if family == "sequence_dp":
        lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        a_lo, a_hi = _range_from_axes(axes, "len_a_range", (0, 20))
        b_lo, b_hi = _range_from_axes(axes, "len_b_range", (0, 20))
        return st.fixed_dictionaries(
            {
                "a": st.lists(
                    st.integers(min_value=lo, max_value=hi),
                    min_size=a_lo,
                    max_size=a_hi,
                ),
                "b": st.lists(
                    st.integers(min_value=lo, max_value=hi),
                    min_size=b_lo,
                    max_size=b_hi,
                ),
            }
        )

    if family == "graph_queries":
        n_nodes = int(getattr(spec_obj, "n_nodes", 1))
        upper = max(0, n_nodes - 1)
        return st.fixed_dictionaries(
            {
                "src": st.integers(min_value=0, max_value=upper),
                "dst": st.integers(min_value=0, max_value=upper),
            }
        )

    raise ValueError(f"Unsupported family for strategy generation: {family}")


def generate_layer2_inputs(
    family: str,
    *,
    task_id: str,
    spec_obj: Any,
    axes: dict[str, Any] | None,
    count: int,
    seed: int = 0,
) -> list[Any]:
    rng = random.Random(_seed_for_task_layer(task_id, "layer2", seed))
    constants = _collect_int_constants(spec_obj.model_dump(mode="python"))

    if family == "piecewise":
        lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        candidates = [lo, hi, 0, 1, -1]
        for constant in constants[:16]:
            candidates.extend([constant - 1, constant, constant + 1])
        while len(candidates) < count:
            candidates.append(rng.randint(lo, hi))
        return candidates[:count]

    if family == "bitops":
        lo, hi = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        width_bits = int(getattr(spec_obj, "width_bits", 8))
        mask = (1 << width_bits) - 1
        candidates = [0, 1, -1, mask, mask + 1, -mask]
        while len(candidates) < count:
            candidates.append(rng.randint(lo, hi))
        return candidates[:count]

    if family in {
        "stateful",
        "simple_algorithms",
        "stack_bytecode",
        "fsm",
        "temporal_logic",
    }:
        value_range = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        length_range = _range_from_axes(
            axes,
            "list_length_range",
            _DEFAULT_LIST_LENGTH_RANGE,
        )
        return _sample_int_lists(
            count=count,
            rng=rng,
            value_range=value_range,
            length_range=length_range,
            constants=constants,
        )

    if family == "stringrules":
        length_range = _range_from_axes(axes, "string_length_range", (0, 20))
        return _sample_string_inputs(
            count=count,
            rng=rng,
            length_range=length_range,
        )

    if family == "intervals":
        endpoint_range = _range_from_axes(
            axes, "endpoint_range", _DEFAULT_INT_RANGE
        )
        list_length_range = _range_from_axes(axes, "n_intervals_range", (0, 10))
        return _sample_intervals_inputs(
            count=count,
            rng=rng,
            endpoint_range=endpoint_range,
            list_length_range=list_length_range,
            constants=constants,
        )

    if family == "sequence_dp":
        value_range = _range_from_axes(axes, "value_range", _DEFAULT_INT_RANGE)
        len_a_range = _range_from_axes(axes, "len_a_range", (0, 20))
        len_b_range = _range_from_axes(axes, "len_b_range", (0, 20))
        return _sample_sequence_dp_inputs(
            count=count,
            rng=rng,
            value_range=value_range,
            len_a_range=len_a_range,
            len_b_range=len_b_range,
            constants=constants,
        )

    if family == "graph_queries":
        n_nodes = int(getattr(spec_obj, "n_nodes", 1))
        return _sample_graph_query_inputs(count=count, rng=rng, n_nodes=n_nodes)

    raise ValueError(f"Unsupported family for layer2 generation: {family}")


def validate_spec_for_task(family: str, spec: Any) -> Any:
    return validate_spec_for_family(family, spec)


def evaluate_input(family: str, spec_obj: Any, input_value: Any) -> Any:
    match family:
        case "piecewise":
            if isinstance(input_value, bool) or not isinstance(
                input_value, int
            ):
                raise TypeError("piecewise input must be int")
            return eval_piecewise(spec_obj, input_value)
        case "stateful":
            if not isinstance(input_value, list):
                raise TypeError("stateful input must be list[int]")
            return eval_stateful(spec_obj, input_value)
        case "simple_algorithms":
            if not isinstance(input_value, list):
                raise TypeError("simple_algorithms input must be list[int]")
            return eval_simple_algorithms(spec_obj, input_value)
        case "stringrules":
            if not isinstance(input_value, str):
                raise TypeError("stringrules input must be str")
            return eval_stringrules(spec_obj, input_value)
        case "stack_bytecode":
            if not isinstance(input_value, list):
                raise TypeError("stack_bytecode input must be list[int]")
            return eval_stack_bytecode(spec_obj, input_value)
        case "fsm":
            if not isinstance(input_value, list):
                raise TypeError("fsm input must be list[int]")
            return eval_fsm(spec_obj, input_value)
        case "bitops":
            if isinstance(input_value, bool) or not isinstance(
                input_value, int
            ):
                raise TypeError("bitops input must be int")
            return eval_bitops(spec_obj, input_value)
        case "sequence_dp":
            if not isinstance(input_value, dict):
                raise TypeError("sequence_dp input must be dict(a,b)")
            a = input_value.get("a")
            b = input_value.get("b")
            if not isinstance(a, list) or not isinstance(b, list):
                raise TypeError("sequence_dp input must include list a/b")
            return eval_sequence_dp(spec_obj, a, b)
        case "intervals":
            if not isinstance(input_value, list):
                raise TypeError("intervals input must be list[tuple[int,int]]")
            return eval_intervals(spec_obj, input_value)
        case "graph_queries":
            if not isinstance(input_value, dict):
                raise TypeError("graph_queries input must be dict(src,dst)")
            src = input_value.get("src")
            dst = input_value.get("dst")
            if isinstance(src, bool) or isinstance(dst, bool):
                raise TypeError("graph_queries src/dst must be int")
            if not isinstance(src, int) or not isinstance(dst, int):
                raise TypeError("graph_queries src/dst must be int")
            return eval_graph_queries(spec_obj, src, dst)
        case "temporal_logic":
            if not isinstance(input_value, list):
                raise TypeError("temporal_logic input must be list[int]")
            return eval_temporal_logic(spec_obj, input_value)
        case _:
            raise ValueError(f"Unknown family '{family}'")
