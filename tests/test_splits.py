from genfxn.core.codegen import get_spec_value
from genfxn.core.models import Query, QueryTag, Task
from genfxn.splits import AxisHoldout, HoldoutType, random_split, split_tasks


def _make_task(task_id: str, spec: dict) -> Task:
    """Helper to create a minimal task for testing."""
    return Task(
        task_id=task_id,
        family="test",
        spec=spec,
        code="def f(): pass",
        queries=[Query(input=0, output=0, tag=QueryTag.TYPICAL)],
    )


class TestGetSpecValue:
    def test_simple_path(self) -> None:
        spec = {"template": "conditional_linear_sum"}
        assert get_spec_value(spec, "template") == "conditional_linear_sum"

    def test_nested_path(self) -> None:
        spec = {"predicate": {"kind": "even"}}
        assert get_spec_value(spec, "predicate.kind") == "even"

    def test_deeply_nested(self) -> None:
        spec = {"a": {"b": {"c": {"d": 42}}}}
        assert get_spec_value(spec, "a.b.c.d") == 42

    def test_list_index(self) -> None:
        spec = {
            "branches": [
                {"condition": {"kind": "lt"}},
                {"condition": {"kind": "ge"}},
            ]
        }
        assert get_spec_value(spec, "branches.0.condition.kind") == "lt"
        assert get_spec_value(spec, "branches.1.condition.kind") == "ge"

    def test_list_index_out_of_bounds(self) -> None:
        spec = {"branches": [{"kind": "lt"}]}
        assert get_spec_value(spec, "branches.5.kind") is None

    def test_missing_path(self) -> None:
        spec = {"predicate": {"kind": "even"}}
        assert get_spec_value(spec, "nonexistent") is None
        assert get_spec_value(spec, "predicate.nonexistent") is None
        assert get_spec_value(spec, "predicate.kind.extra") is None

    def test_empty_spec(self) -> None:
        assert get_spec_value({}, "anything") is None

    def test_non_dict_intermediate(self) -> None:
        spec = {"template": "value"}
        assert get_spec_value(spec, "template.nested") is None


class TestSplitTasks:
    def test_exact_holdout(self) -> None:
        tasks = [
            _make_task("t1", {"template": "conditional_linear_sum"}),
            _make_task("t2", {"template": "longest_run"}),
            _make_task("t3", {"template": "conditional_linear_sum"}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="template",
                holdout_type=HoldoutType.EXACT,
                holdout_value="longest_run",
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 2
        assert len(result.test) == 1
        assert result.test[0].task_id == "t2"
        assert all(
            t.spec["template"] == "conditional_linear_sum" for t in result.train
        )

    def test_nested_exact_holdout(self) -> None:
        tasks = [
            _make_task("t1", {"predicate": {"kind": "even"}}),
            _make_task("t2", {"predicate": {"kind": "mod_eq", "divisor": 3}}),
            _make_task("t3", {"predicate": {"kind": "lt", "value": 5}}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="predicate.kind",
                holdout_type=HoldoutType.EXACT,
                holdout_value="mod_eq",
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 2
        assert len(result.test) == 1
        assert result.test[0].task_id == "t2"

    def test_range_holdout(self) -> None:
        tasks = [
            _make_task("t1", {"threshold": 5}),
            _make_task("t2", {"threshold": 15}),
            _make_task("t3", {"threshold": 25}),
            _make_task("t4", {"threshold": 35}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="threshold",
                holdout_type=HoldoutType.RANGE,
                holdout_value=(10, 30),
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 2
        assert len(result.test) == 2
        assert {t.task_id for t in result.test} == {"t2", "t3"}

    def test_range_inclusive_bounds(self) -> None:
        tasks = [
            _make_task("t1", {"value": 10}),
            _make_task("t2", {"value": 20}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="value",
                holdout_type=HoldoutType.RANGE,
                holdout_value=(10, 20),
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 0
        assert len(result.test) == 2

    def test_contains_holdout(self) -> None:
        tasks = [
            _make_task("t1", {"tags": ["fast", "simple"]}),
            _make_task("t2", {"tags": ["complex", "slow"]}),
            _make_task("t3", {"tags": ["fast", "complex"]}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="tags",
                holdout_type=HoldoutType.CONTAINS,
                holdout_value="complex",
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 1
        assert len(result.test) == 2
        assert result.train[0].task_id == "t1"

    def test_multiple_holdouts_or_logic(self) -> None:
        tasks = [
            _make_task("t1", {"template": "a", "predicate": {"kind": "even"}}),
            _make_task("t2", {"template": "b", "predicate": {"kind": "odd"}}),
            _make_task("t3", {"template": "a", "predicate": {"kind": "odd"}}),
            _make_task("t4", {"template": "c", "predicate": {"kind": "lt"}}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="template",
                holdout_type=HoldoutType.EXACT,
                holdout_value="b",
            ),
            AxisHoldout(
                axis_path="predicate.kind",
                holdout_type=HoldoutType.EXACT,
                holdout_value="even",
            ),
        ]
        result = split_tasks(tasks, holdouts)

        # t1 matches even, t2 matches template b -> both in test
        assert len(result.test) == 2
        assert {t.task_id for t in result.test} == {"t1", "t2"}
        assert len(result.train) == 2
        assert {t.task_id for t in result.train} == {"t3", "t4"}

    def test_empty_tasks(self) -> None:
        holdouts = [
            AxisHoldout(
                axis_path="template",
                holdout_type=HoldoutType.EXACT,
                holdout_value="x",
            )
        ]
        result = split_tasks([], holdouts)

        assert result.train == []
        assert result.test == []
        assert result.holdouts == holdouts

    def test_empty_holdouts(self) -> None:
        tasks = [_make_task("t1", {"a": 1}), _make_task("t2", {"a": 2})]
        result = split_tasks(tasks, [])

        assert len(result.train) == 2
        assert result.test == []

    def test_no_matches(self) -> None:
        tasks = [
            _make_task("t1", {"template": "a"}),
            _make_task("t2", {"template": "b"}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="template",
                holdout_type=HoldoutType.EXACT,
                holdout_value="c",
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 2
        assert result.test == []

    def test_all_match(self) -> None:
        tasks = [
            _make_task("t1", {"template": "a"}),
            _make_task("t2", {"template": "a"}),
        ]
        holdouts = [
            AxisHoldout(
                axis_path="template",
                holdout_type=HoldoutType.EXACT,
                holdout_value="a",
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert result.train == []
        assert len(result.test) == 2

    def test_missing_path_does_not_match(self) -> None:
        tasks = [
            _make_task("t1", {"template": "a"}),
            _make_task("t2", {}),  # missing template
        ]
        holdouts = [
            AxisHoldout(
                axis_path="template",
                holdout_type=HoldoutType.EXACT,
                holdout_value="a",
            )
        ]
        result = split_tasks(tasks, holdouts)

        assert len(result.train) == 1
        assert result.train[0].task_id == "t2"
        assert len(result.test) == 1
        assert result.test[0].task_id == "t1"

    def test_split_result_preserves_holdouts(self) -> None:
        tasks = [_make_task("t1", {"x": 1})]
        holdouts = [
            AxisHoldout(
                axis_path="x", holdout_type=HoldoutType.EXACT, holdout_value=1
            ),
            AxisHoldout(
                axis_path="y",
                holdout_type=HoldoutType.RANGE,
                holdout_value=(0, 10),
            ),
        ]
        result = split_tasks(tasks, holdouts)

        assert result.holdouts == holdouts
        assert len(result.holdouts) == 2


class TestRandomSplit:
    def test_basic_split_ratio(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(100)]
        result = random_split(tasks, train_ratio=0.8, seed=42)

        assert len(result.train) == 80
        assert len(result.test) == 20

    def test_different_ratios(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(100)]

        result_90 = random_split(tasks, train_ratio=0.9, seed=42)
        assert len(result_90.train) == 90
        assert len(result_90.test) == 10

        result_50 = random_split(tasks, train_ratio=0.5, seed=42)
        assert len(result_50.train) == 50
        assert len(result_50.test) == 50

        result_10 = random_split(tasks, train_ratio=0.1, seed=42)
        assert len(result_10.train) == 10
        assert len(result_10.test) == 90

    def test_reproducibility_same_seed(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(50)]

        result1 = random_split(tasks, train_ratio=0.8, seed=123)
        result2 = random_split(tasks, train_ratio=0.8, seed=123)

        train1_ids = [t.task_id for t in result1.train]
        train2_ids = [t.task_id for t in result2.train]
        assert train1_ids == train2_ids

        test1_ids = [t.task_id for t in result1.test]
        test2_ids = [t.task_id for t in result2.test]
        assert test1_ids == test2_ids

    def test_different_seeds_different_results(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(50)]

        result1 = random_split(tasks, train_ratio=0.8, seed=1)
        result2 = random_split(tasks, train_ratio=0.8, seed=2)

        # Very unlikely to be the same with different seeds
        train_ids_1 = {t.task_id for t in result1.train}
        train_ids_2 = {t.task_id for t in result2.train}
        assert train_ids_1 != train_ids_2

    def test_no_seed_works(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(20)]
        result = random_split(tasks, train_ratio=0.8, seed=None)

        assert len(result.train) == 16
        assert len(result.test) == 4

    def test_preserves_all_tasks(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(100)]
        result = random_split(tasks, train_ratio=0.7, seed=42)

        train_ids = {t.task_id for t in result.train}
        test_ids = {t.task_id for t in result.test}
        all_ids = train_ids | test_ids
        original_ids = {t.task_id for t in tasks}

        assert all_ids == original_ids
        assert len(result.train) + len(result.test) == len(tasks)

    def test_no_duplicates(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(50)]
        result = random_split(tasks, train_ratio=0.8, seed=42)

        train_ids = [t.task_id for t in result.train]
        test_ids = [t.task_id for t in result.test]

        assert len(train_ids) == len(set(train_ids))
        assert len(test_ids) == len(set(test_ids))
        assert set(train_ids).isdisjoint(set(test_ids))

    def test_empty_tasks(self) -> None:
        result = random_split([], train_ratio=0.8, seed=42)

        assert result.train == []
        assert result.test == []

    def test_single_task_train(self) -> None:
        tasks = [_make_task("t1", {"x": 1})]
        result = random_split(tasks, train_ratio=0.8, seed=42)

        # With ratio 0.8, int(1 * 0.8) = 0, so 0 train, 1 test
        assert len(result.train) == 0
        assert len(result.test) == 1

    def test_single_task_test(self) -> None:
        tasks = [_make_task("t1", {"x": 1})]
        result = random_split(tasks, train_ratio=0.2, seed=42)

        # With ratio 0.2, int(1 * 0.2) = 0, so 0 train, 1 test
        assert len(result.train) == 0
        assert len(result.test) == 1

    def test_holdouts_empty(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(10)]
        result = random_split(tasks, train_ratio=0.8, seed=42)

        assert result.holdouts == []

    def test_does_not_modify_original(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(20)]
        original_order = [t.task_id for t in tasks]

        random_split(tasks, train_ratio=0.8, seed=42)

        assert [t.task_id for t in tasks] == original_order

    def test_shuffles_tasks(self) -> None:
        tasks = [_make_task(f"t{i}", {"x": i}) for i in range(50)]
        result = random_split(tasks, train_ratio=0.8, seed=42)

        # Check that train set isn't just the first N tasks
        original_first_40_ids = {f"t{i}" for i in range(40)}
        train_ids = {t.task_id for t in result.train}
        assert train_ids != original_first_40_ids
