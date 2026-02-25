from __future__ import annotations

import copy
import json
import logging
import math
import random
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from genfxn.core.models import Task
from genfxn.verification.adapters import (
    evaluate_input,
    generate_layer2_inputs,
    validate_spec_for_task,
)
from genfxn.verification.models import (
    MutationCurvePoint,
    VerificationCase,
    VerificationLayer,
    normalize_case_value,
)

# Keep mutations within signed i64 to maintain Python/Java/Rust parity.
I64_MIN = -(1 << 63)
# Keep mutations within signed i64 to maintain Python/Java/Rust parity.
I64_MAX = (1 << 63) - 1
_CURVE_POINTS = (1, 2, 3, 4, 6, 8, 12, 16, 20, 24)
_SWAP_MAP: dict[str, str] = {
    "lt": "le",
    "le": "lt",
    "gt": "ge",
    "ge": "gt",
    "and": "or",
    "or": "and",
    "smallest": "first_seen",
    "first_seen": "smallest",
    "all_indices": "unique_values",
    "unique_values": "all_indices",
    "sat_at_start": "sat_count",
    "sat_count": "first_sat_index",
    "first_sat_index": "sat_at_start",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Layer3Summary:
    cases: list[VerificationCase]
    mutation_score: float
    mutation_score_curve: list[MutationCurvePoint]
    heldout_mutant_fpr: float
    heldout_mutant_fpr_ci95: float
    heldout_distinguishable_mutants: int
    heldout_mutant_escapes: int


def _iter_mutation_candidates(
    value: Any,
    path: tuple[Any, ...] = (),
) -> list[tuple[tuple[Any, ...], Any, str]]:
    candidates: list[tuple[tuple[Any, ...], Any, str]] = []

    if isinstance(value, bool):
        candidates.append((path, not value, "bool_flip"))
        return candidates

    if isinstance(value, int):
        if value > I64_MIN:
            candidates.append((path, value - 1, "int_minus_one"))
        if value < I64_MAX:
            candidates.append((path, value + 1, "int_plus_one"))
        if value != 0:
            candidates.append((path, 0, "int_to_zero"))
        return candidates

    if isinstance(value, str):
        replacement = _SWAP_MAP.get(value)
        if replacement is not None and replacement != value:
            candidates.append((path, replacement, "enum_swap"))
        return candidates

    if isinstance(value, list):
        for idx, item in enumerate(value):
            candidates.extend(_iter_mutation_candidates(item, (*path, idx)))
        if len(value) >= 2:
            swapped = list(value)
            swapped[0], swapped[1] = swapped[1], swapped[0]
            candidates.append((path, swapped, "swap_first_two"))
        return candidates

    if isinstance(value, dict):
        for key, item in value.items():
            candidates.extend(_iter_mutation_candidates(item, (*path, key)))
        return candidates

    return candidates


def _set_at_path(root: Any, path: tuple[Any, ...], value: Any) -> Any:
    """Set a value at path.

    For ``_set_at_path(root: Any, path: tuple[Any, ...], value: Any)``, an
    empty ``path`` returns ``value`` (replacing/discarding the original root).
    A non-empty ``path`` mutates ``root`` in place along the path and returns
    the same root reference. Callers should deep-copy before calling.
    """
    if len(path) == 0:
        return value

    node = root
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return root


def _spec_hash(spec: Any) -> str:
    payload = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _heldout_seed(seed: int) -> int:
    digest = sha256(f"heldout:{seed}".encode()).digest()
    derived = int.from_bytes(digest[:8], byteorder="big", signed=False)
    if derived == seed:
        return derived ^ (1 << 63)
    return derived


def _canonical_input_key(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except TypeError:
        return repr(value)


def _dedupe_inputs(values: list[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = _canonical_input_key(value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _extend_candidate_inputs(
    *,
    task: Task,
    spec_obj: Any,
    base_inputs: list[Any],
    seed: int,
    target_count: int = 256,
    max_batches: int = 8,
    batch_count: int = 64,
) -> list[Any]:
    candidates = _dedupe_inputs(base_inputs)
    if len(candidates) >= target_count:
        return candidates

    seen = {_canonical_input_key(value) for value in candidates}
    for batch in range(max_batches):
        try:
            sampled = generate_layer2_inputs(
                task.family,
                task_id=task.task_id,
                spec_obj=spec_obj,
                axes=task.axes,
                count=batch_count,
                seed=seed + 10_000 + batch,
            )
        except Exception as exc:
            logger.debug(
                "Failed to extend mutation candidate inputs for task %s: %s",
                task.task_id,
                exc,
                exc_info=True,
            )
            break

        for value in sampled:
            key = _canonical_input_key(value)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(value)
            if len(candidates) >= target_count:
                return candidates
    return candidates


def _find_witness(
    *,
    task: Task,
    spec_obj: Any,
    mutant_obj: Any,
    candidate_inputs: list[Any],
    debug_context: str,
) -> tuple[Any | None, Any | None]:
    for input_value in candidate_inputs:
        try:
            differs, expected = _distinguishes(
                family=task.family,
                spec_obj=spec_obj,
                mutant_obj=mutant_obj,
                input_value=input_value,
            )
        except Exception as exc:
            logger.debug(
                "Skipping %s for task %s input=%r: %s",
                debug_context,
                task.task_id,
                input_value,
                exc,
                exc_info=True,
            )
            continue
        if differs:
            return input_value, expected
    return None, None


def _generate_valid_mutants(
    *,
    family: str,
    spec: dict[str, Any],
    budget: int,
    seed: int,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    candidates = _iter_mutation_candidates(spec)
    rng.shuffle(candidates)

    mutants: list[dict[str, Any]] = []
    seen_hashes = {_spec_hash(spec)}
    for path, replacement, _kind in candidates:
        if len(mutants) >= budget:
            break
        mutated = copy.deepcopy(spec)
        _set_at_path(mutated, path, replacement)
        digest = _spec_hash(mutated)
        if digest in seen_hashes:
            continue

        try:
            _ = validate_spec_for_task(family, mutated)
        except Exception as exc:
            logger.debug(
                "Skipping mutated spec during validation: %s",
                exc,
                exc_info=True,
            )
            continue

        seen_hashes.add(digest)
        mutants.append(mutated)

    return mutants


def _distinguishes(
    *,
    family: str,
    spec_obj: Any,
    mutant_obj: Any,
    input_value: Any,
) -> tuple[bool, Any]:
    expected = normalize_case_value(
        evaluate_input(family, spec_obj, input_value)
    )
    actual = normalize_case_value(
        evaluate_input(family, mutant_obj, input_value)
    )
    return expected != actual, expected


def _ci95_for_rate(rate: float, n: int) -> float:
    if n <= 0:
        return 0.0
    return 1.96 * math.sqrt(rate * (1.0 - rate) / n)


def generate_layer3_cases(
    task: Task,
    *,
    layer1_inputs: list[Any],
    layer2_inputs: list[Any],
    budget: int = 24,
    heldout_mutants: int = 50,
    seed: int = 0,
) -> Layer3Summary:
    spec_obj = validate_spec_for_task(task.family, task.spec)

    mutants = _generate_valid_mutants(
        family=task.family,
        spec=task.spec,
        budget=budget,
        seed=seed,
    )

    candidate_inputs = _extend_candidate_inputs(
        task=task,
        spec_obj=spec_obj,
        base_inputs=[*layer1_inputs, *layer2_inputs],
        seed=seed,
    )

    cases: list[VerificationCase] = []
    kill_case_index: dict[int, int] = {}
    distinguishable_mutants: set[int] = set()

    for mutant_index, mutant_spec in enumerate(mutants):
        mutant_obj = validate_spec_for_task(task.family, mutant_spec)
        witness, expected = _find_witness(
            task=task,
            spec_obj=spec_obj,
            mutant_obj=mutant_obj,
            candidate_inputs=candidate_inputs,
            debug_context=(
                f"mutation candidate input mutant_index={mutant_index}"
            ),
        )
        if witness is None:
            continue

        distinguishable_mutants.add(mutant_index)
        if len(cases) >= budget:
            continue

        case_index = len(cases)
        cases.append(
            VerificationCase(
                task_id=task.task_id,
                family=task.family,
                layer=VerificationLayer.LAYER3_MUTATION,
                case_id=f"layer3-{case_index:04d}",
                input=witness,
                expected_output=expected,
                seed=seed,
                source_detail={
                    "mutant_index": mutant_index,
                    "mutant_hash": _spec_hash(mutant_spec),
                },
            )
        )
        kill_case_index[mutant_index] = case_index

    total_mutants = len(distinguishable_mutants)
    killed_mutants = len(kill_case_index)
    mutation_score = (killed_mutants / total_mutants) if total_mutants else 1.0

    curve: list[MutationCurvePoint] = []
    for n_tests in _CURVE_POINTS:
        if total_mutants == 0:
            score_at_n = 1.0
        else:
            # The curve uses case insertion order (`idx`) as the proxy for
            # "first N tests". If a different ordering policy is desired,
            # options include randomizing case order, sorting by effectiveness,
            # or recomputing by unique test-case counts.
            killed_at_n = sum(
                1 for idx in kill_case_index.values() if idx < n_tests
            )
            score_at_n = killed_at_n / total_mutants
        curve.append(
            MutationCurvePoint(n_tests=n_tests, mutation_score=score_at_n)
        )

    heldout = _generate_valid_mutants(
        family=task.family,
        spec=task.spec,
        budget=heldout_mutants,
        seed=_heldout_seed(seed),
    )
    heldout_distinguishable = 0
    heldout_escapes = 0
    heldout_inputs = [
        *layer1_inputs,
        *layer2_inputs,
        *(case.input for case in cases),
    ]
    for mutant_spec in heldout:
        mutant_obj = validate_spec_for_task(task.family, mutant_spec)
        witness, _ = _find_witness(
            task=task,
            spec_obj=spec_obj,
            mutant_obj=mutant_obj,
            candidate_inputs=candidate_inputs,
            debug_context="heldout distinguishability probe",
        )
        if witness is None:
            continue

        heldout_distinguishable += 1
        detected_input, _ = _find_witness(
            task=task,
            spec_obj=spec_obj,
            mutant_obj=mutant_obj,
            candidate_inputs=heldout_inputs,
            debug_context="heldout mutation check",
        )
        if detected_input is None:
            heldout_escapes += 1

    heldout_mutant_fpr = (
        heldout_escapes / heldout_distinguishable
        if heldout_distinguishable
        else 0.0
    )
    heldout_mutant_fpr_ci95 = _ci95_for_rate(
        heldout_mutant_fpr,
        heldout_distinguishable,
    )

    return Layer3Summary(
        cases=cases,
        mutation_score=mutation_score,
        mutation_score_curve=curve,
        heldout_mutant_fpr=heldout_mutant_fpr,
        heldout_mutant_fpr_ci95=heldout_mutant_fpr_ci95,
        heldout_distinguishable_mutants=heldout_distinguishable,
        heldout_mutant_escapes=heldout_escapes,
    )
