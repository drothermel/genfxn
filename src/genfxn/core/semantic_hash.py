from __future__ import annotations

import hashlib
import random
import string
from collections.abc import Callable
from importlib import import_module
from typing import Any

import srsly

from genfxn.core.canonicalization import canonical_spec_bytes
from genfxn.core.codegen import _canonicalize_for_hash
from genfxn.core.spec_registry import validate_spec_for_family

SEM_HASH_V1 = "sem_hash_v1"
_DEFAULT_RANDOM_PROBES = 24

_EVAL_IMPORTS: dict[str, tuple[str, str]] = {
    "piecewise": ("genfxn.piecewise.eval", "eval_piecewise"),
    "stateful": ("genfxn.stateful.eval", "eval_stateful"),
    "simple_algorithms": (
        "genfxn.simple_algorithms.eval",
        "eval_simple_algorithms",
    ),
    "stringrules": ("genfxn.stringrules.eval", "eval_stringrules"),
    "stack_bytecode": ("genfxn.stack_bytecode.eval", "eval_stack_bytecode"),
    "fsm": ("genfxn.fsm.eval", "eval_fsm"),
    "bitops": ("genfxn.bitops.eval", "eval_bitops"),
    "sequence_dp": ("genfxn.sequence_dp.eval", "eval_sequence_dp"),
    "intervals": ("genfxn.intervals.eval", "eval_intervals"),
    "graph_queries": ("genfxn.graph_queries.eval", "eval_graph_queries"),
    "temporal_logic": ("genfxn.temporal_logic.eval", "eval_temporal_logic"),
}
_EVALUATORS: dict[str, Callable[..., Any]] = {}


def _seed_for_family_spec(family: str, spec: Any) -> int:
    digest = hashlib.sha256(canonical_spec_bytes(family, spec)).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _rng_for_family_spec(family: str, spec: Any) -> random.Random:
    return random.Random(_seed_for_family_spec(family, spec))


def _collect_small_int_constants(value: Any) -> list[int]:
    collected: list[int] = []

    def _visit(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int):
            if -512 <= node <= 512:
                collected.append(node)
            return
        if isinstance(node, list | tuple | set | frozenset):
            for item in node:
                _visit(item)
            return
        if isinstance(node, dict):
            for item in node.values():
                _visit(item)
            return

    _visit(value)
    deduped = sorted(set(collected))
    if len(deduped) > 16:
        return deduped[:16]
    return deduped


def _base_int_lists(rng: random.Random) -> list[list[int]]:
    probes: list[list[int]] = [
        [],
        [0],
        [1],
        [-1],
        [0, 0],
        [1, -1],
        [2, -2, 3],
        [-3, 3, -3, 3],
        [7] * 5,
    ]
    for _ in range(_DEFAULT_RANDOM_PROBES):
        length = rng.randint(0, 6)
        probes.append([rng.randint(-9, 9) for _ in range(length)])
    return probes


def _base_strings(rng: random.Random) -> list[str]:
    probes = [
        "",
        "a",
        "A",
        "0",
        "abc",
        "ABC",
        "a1B2",
        "  spaced  ",
        "a_b",
        "ababab",
    ]
    alphabet = string.ascii_letters + string.digits + " _-"
    for _ in range(_DEFAULT_RANDOM_PROBES):
        length = rng.randint(0, 10)
        probes.append("".join(rng.choice(alphabet) for _ in range(length)))
    return probes


def _probes_piecewise(spec: Any, rng: random.Random) -> list[int]:
    values = [-6, -3, -2, -1, 0, 1, 2, 3, 6]
    for constant in _collect_small_int_constants(
        spec.model_dump(mode="python")
    ):
        values.extend([constant - 1, constant, constant + 1])
    for _ in range(_DEFAULT_RANDOM_PROBES):
        values.append(rng.randint(-100, 100))
    ordered = sorted(set(values))
    return ordered


def _probes_stateful(_spec: Any, rng: random.Random) -> list[list[int]]:
    return _base_int_lists(rng)


def _probes_simple_algorithms(
    _spec: Any, rng: random.Random
) -> list[list[int]]:
    return _base_int_lists(rng)


def _probes_stringrules(_spec: Any, rng: random.Random) -> list[str]:
    return _base_strings(rng)


def _probes_stack_bytecode(_spec: Any, rng: random.Random) -> list[list[int]]:
    probes = _base_int_lists(rng)
    probes.extend([[0] * 12, [1, -1] * 8])
    return probes


def _probes_fsm(_spec: Any, rng: random.Random) -> list[list[int]]:
    probes = _base_int_lists(rng)
    probes.extend([[0] * 10, [1, -1] * 7, [3, 3, 3, 3, 3]])
    return probes


def _probes_bitops(spec: Any, rng: random.Random) -> list[int]:
    if spec.width_bits <= 10:
        return list(range(1 << spec.width_bits))

    mask = (1 << spec.width_bits) - 1
    probes = [0, 1, -1, mask, mask + 1, -(mask + 1)]
    for _ in range(_DEFAULT_RANDOM_PROBES * 2):
        probes.append(rng.randint(-(1 << 20), (1 << 20)))
    return probes


def _probes_sequence_dp(
    _spec: Any, rng: random.Random
) -> list[dict[str, list[int]]]:
    pool = _base_int_lists(rng)
    probes: list[dict[str, list[int]]] = []
    for left in pool[:16]:
        for right in pool[:4]:
            probes.append({"a": left, "b": right})
    for _ in range(_DEFAULT_RANDOM_PROBES):
        len_a = rng.randint(0, 6)
        len_b = rng.randint(0, 6)
        probes.append(
            {
                "a": [rng.randint(-8, 8) for _ in range(len_a)],
                "b": [rng.randint(-8, 8) for _ in range(len_b)],
            }
        )
    return probes


def _probes_intervals(
    _spec: Any, rng: random.Random
) -> list[list[tuple[int, int]]]:
    probes: list[list[tuple[int, int]]] = [
        [],
        [(0, 0)],
        [(0, 1)],
        [(1, 0)],
        [(-3, 2), (2, 8)],
        [(-5, -2), (-4, 3), (10, 15)],
        [(-1, 1), (-1, 1), (-1, 1)],
    ]
    for _ in range(_DEFAULT_RANDOM_PROBES):
        length = rng.randint(0, 6)
        candidate: list[tuple[int, int]] = []
        for _ in range(length):
            a = rng.randint(-20, 20)
            b = rng.randint(-20, 20)
            candidate.append((a, b))
        probes.append(candidate)
    return probes


def _probes_graph_queries(
    spec: Any, rng: random.Random
) -> list[dict[str, int]]:
    if spec.n_nodes <= 8:
        return [
            {"src": src, "dst": dst}
            for src in range(spec.n_nodes)
            for dst in range(spec.n_nodes)
        ]

    probes = [
        {"src": 0, "dst": 0},
        {"src": 0, "dst": spec.n_nodes - 1},
        {"src": spec.n_nodes - 1, "dst": 0},
        {"src": spec.n_nodes - 1, "dst": spec.n_nodes - 1},
    ]
    for _ in range(_DEFAULT_RANDOM_PROBES * 2):
        probes.append(
            {
                "src": rng.randrange(spec.n_nodes),
                "dst": rng.randrange(spec.n_nodes),
            }
        )
    return probes


def _probes_temporal_logic(_spec: Any, rng: random.Random) -> list[list[int]]:
    probes = _base_int_lists(rng)
    probes.extend([[0] * 16, [1, 0, 1, 0, 1, 0], [-2, -1, 0, 1, 2]])
    return probes


def _get_raw_evaluator(family: str) -> Callable[..., Any]:
    evaluator = _EVALUATORS.get(family)
    if evaluator is not None:
        return evaluator

    target = _EVAL_IMPORTS.get(family)
    if target is None:
        supported = ", ".join(sorted(_EVAL_IMPORTS))
        raise ValueError(f"Unknown family '{family}'. Supported: {supported}")

    module_name, function_name = target
    module = import_module(module_name)
    evaluator = getattr(module, function_name)
    _EVALUATORS[family] = evaluator
    return evaluator


def _eval_piecewise(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("piecewise")(spec, probe)


def _eval_stateful(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("stateful")(spec, probe)


def _eval_simple_algorithms(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("simple_algorithms")(spec, probe)


def _eval_stringrules(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("stringrules")(spec, probe)


def _eval_stack_bytecode(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("stack_bytecode")(spec, probe)


def _eval_fsm(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("fsm")(spec, probe)


def _eval_bitops(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("bitops")(spec, probe)


def _eval_sequence_dp(spec: Any, probe: Any) -> Any:
    if not isinstance(probe, dict):
        raise ValueError("sequence_dp probe must be dict")
    a = probe.get("a")
    b = probe.get("b")
    if not isinstance(a, list) or not isinstance(b, list):
        raise ValueError("sequence_dp probe missing list args")
    return _get_raw_evaluator("sequence_dp")(spec, a, b)


def _eval_intervals(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("intervals")(spec, probe)


def _eval_graph_queries(spec: Any, probe: Any) -> Any:
    if not isinstance(probe, dict):
        raise ValueError("graph_queries probe must be dict")
    src = probe.get("src")
    dst = probe.get("dst")
    if not isinstance(src, int) or not isinstance(dst, int):
        raise ValueError("graph_queries probe missing int src/dst")
    return _get_raw_evaluator("graph_queries")(spec, src, dst)


def _eval_temporal_logic(spec: Any, probe: Any) -> Any:
    return _get_raw_evaluator("temporal_logic")(spec, probe)


_ProbeFactory = Callable[[Any, random.Random], list[Any]]
_ProbeEvaluator = Callable[[Any, Any], Any]

_SEMANTIC_REGISTRY: dict[str, tuple[_ProbeFactory, _ProbeEvaluator]] = {
    "piecewise": (_probes_piecewise, _eval_piecewise),
    "stateful": (_probes_stateful, _eval_stateful),
    "simple_algorithms": (_probes_simple_algorithms, _eval_simple_algorithms),
    "stringrules": (_probes_stringrules, _eval_stringrules),
    "stack_bytecode": (_probes_stack_bytecode, _eval_stack_bytecode),
    "fsm": (_probes_fsm, _eval_fsm),
    "bitops": (_probes_bitops, _eval_bitops),
    "sequence_dp": (_probes_sequence_dp, _eval_sequence_dp),
    "intervals": (_probes_intervals, _eval_intervals),
    "graph_queries": (_probes_graph_queries, _eval_graph_queries),
    "temporal_logic": (_probes_temporal_logic, _eval_temporal_logic),
}


def compute_sem_hash(
    family: str,
    spec: Any,
) -> str:
    registry_entry = _SEMANTIC_REGISTRY.get(family)
    if registry_entry is None:
        supported = ", ".join(sorted(_SEMANTIC_REGISTRY))
        raise ValueError(f"Unknown family '{family}'. Supported: {supported}")

    probe_factory, evaluator = registry_entry
    spec_obj = validate_spec_for_family(family, spec)
    rng = _rng_for_family_spec(family, spec_obj)
    probes = probe_factory(spec_obj, rng)

    output_vector: list[dict[str, Any]] = []
    for probe in probes:
        try:
            result = evaluator(spec_obj, probe)
        except Exception as exc:
            result = {
                "__error__": {
                    "message": str(exc),
                    "type": type(exc).__name__,
                }
            }
        output_vector.append({"probe": probe, "result": result})

    payload = {
        "family": family,
        "outputs": output_vector,
        "version": SEM_HASH_V1,
    }
    canonical = srsly.json_dumps(
        _canonicalize_for_hash(payload), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
