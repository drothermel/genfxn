import random

from genfxn.core.family_registry import generate_task_for_family
from genfxn.verification.adapters import (
    generate_layer3_mutants,
    get_registered_families,
    validate_spec_for_task,
)
from genfxn.verification.adapters.mutations import stable_spec_hash


def test_all_registered_adapters_implement_layer3_mutants() -> None:
    for index, family in enumerate(get_registered_families()):
        task = generate_task_for_family(family, rng=random.Random(100 + index))
        spec_obj = validate_spec_for_task(family, task.spec)
        mutants = generate_layer3_mutants(
            family,
            task_id=task.task_id,
            spec_obj=spec_obj,
            spec_dict=task.spec,
            budget=8,
            seed=17,
            mode="train",
        )
        assert isinstance(mutants, list)
        for mutant in mutants:
            assert mutant.rule_id.startswith(f"{family}.")
            _ = validate_spec_for_task(family, mutant.mutant_spec)


def test_layer3_mutants_are_deterministic_for_same_seed() -> None:
    task = generate_task_for_family("piecewise", rng=random.Random(7))
    spec_obj = validate_spec_for_task(task.family, task.spec)

    first = generate_layer3_mutants(
        task.family,
        task_id=task.task_id,
        spec_obj=spec_obj,
        spec_dict=task.spec,
        budget=24,
        seed=99,
        mode="train",
    )
    second = generate_layer3_mutants(
        task.family,
        task_id=task.task_id,
        spec_obj=spec_obj,
        spec_dict=task.spec,
        budget=24,
        seed=99,
        mode="train",
    )

    first_hashes = [stable_spec_hash(item.mutant_spec) for item in first]
    second_hashes = [stable_spec_hash(item.mutant_spec) for item in second]
    assert first_hashes == second_hashes
    assert [item.rule_id for item in first] == [item.rule_id for item in second]


def test_layer3_train_and_heldout_mutants_are_disjoint() -> None:
    task = generate_task_for_family("piecewise", rng=random.Random(13))
    spec_obj = validate_spec_for_task(task.family, task.spec)
    train = generate_layer3_mutants(
        task.family,
        task_id=task.task_id,
        spec_obj=spec_obj,
        spec_dict=task.spec,
        budget=24,
        seed=11,
        mode="train",
    )
    heldout = generate_layer3_mutants(
        task.family,
        task_id=task.task_id,
        spec_obj=spec_obj,
        spec_dict=task.spec,
        budget=24,
        seed=11,
        mode="heldout",
    )
    train_hashes = {stable_spec_hash(item.mutant_spec) for item in train}
    heldout_hashes = {stable_spec_hash(item.mutant_spec) for item in heldout}
    assert train_hashes.isdisjoint(heldout_hashes)
