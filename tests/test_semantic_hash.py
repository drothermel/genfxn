import random

from genfxn.bitops.models import BitInstruction, BitOp, BitopsSpec
from genfxn.bitops.task import generate_bitops_task
from genfxn.core.semantic_hash import _probes_bitops, compute_sem_hash
from genfxn.core.task_ids import validate_task_ids
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.task import generate_intervals_task
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.temporal_logic.task import generate_temporal_logic_task


def test_sem_hash_deterministic_for_same_spec() -> None:
    spec = {
        "width_bits": 8,
        "operations": [{"op": "xor_mask", "arg": 15}],
    }
    sem_a = compute_sem_hash("bitops", spec)
    sem_b = compute_sem_hash("bitops", spec)
    assert sem_a == sem_b


def test_sem_hash_equivalent_graph_specs_match() -> None:
    spec_a = {
        "query_type": "shortest_path_cost",
        "directed": False,
        "weighted": True,
        "n_nodes": 3,
        "edges": [
            {"u": 0, "v": 1, "w": 9},
            {"u": 1, "v": 0, "w": 2},
        ],
    }
    spec_b = {
        "query_type": "shortest_path_cost",
        "directed": False,
        "weighted": True,
        "n_nodes": 3,
        "edges": [{"u": 0, "v": 1, "w": 2}],
    }
    assert compute_sem_hash("graph_queries", spec_a) == compute_sem_hash(
        "graph_queries", spec_b
    )


def test_sem_hash_distinguishes_non_equivalent_specs() -> None:
    spec_a = {
        "width_bits": 8,
        "operations": [{"op": "xor_mask", "arg": 1}],
    }
    spec_b = {
        "width_bits": 8,
        "operations": [{"op": "xor_mask", "arg": 2}],
    }
    assert compute_sem_hash("bitops", spec_a) != compute_sem_hash(
        "bitops", spec_b
    )


def test_bitops_exhaustive_probe_domain_small_width() -> None:
    spec_small = BitopsSpec(
        width_bits=10,
        operations=[BitInstruction(op=BitOp.NOT)],
    )
    spec_large = BitopsSpec(
        width_bits=12,
        operations=[BitInstruction(op=BitOp.NOT)],
    )

    probes_small = _probes_bitops(spec_small, random.Random(1))
    probes_large = _probes_bitops(spec_large, random.Random(1))

    assert probes_small == list(range(1 << 10))
    assert len(probes_large) != (1 << 12)


def test_generated_tasks_have_non_empty_sem_hash_all_families() -> None:
    generators = [
        lambda: generate_piecewise_task(rng=random.Random(1)),
        lambda: generate_stateful_task(rng=random.Random(1)),
        lambda: generate_simple_algorithms_task(rng=random.Random(1)),
        lambda: generate_stringrules_task(rng=random.Random(1)),
        lambda: generate_stack_bytecode_task(rng=random.Random(1)),
        lambda: generate_fsm_task(rng=random.Random(1)),
        lambda: generate_bitops_task(rng=random.Random(1)),
        lambda: generate_sequence_dp_task(rng=random.Random(1)),
        lambda: generate_intervals_task(rng=random.Random(1)),
        lambda: generate_graph_queries_task(rng=random.Random(1)),
        lambda: generate_temporal_logic_task(rng=random.Random(1)),
    ]
    for make_task in generators:
        task = make_task()
        assert isinstance(task.sem_hash, str) and task.sem_hash
        assert validate_task_ids(task) == []
