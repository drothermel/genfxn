from genfxn.core.codegen import get_spec_value
from genfxn.core.models import Query, QueryTag, Task
from genfxn.splits import AxisHoldout, HoldoutType, split_tasks


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
            "branches": [{"condition": {"kind": "lt"}}, {"condition": {"kind": "ge"}}]
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
        assert all(t.spec["template"] == "conditional_linear_sum" for t in result.train)

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
                axis_path="template", holdout_type=HoldoutType.EXACT, holdout_value="b"
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
                axis_path="template", holdout_type=HoldoutType.EXACT, holdout_value="x"
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
                axis_path="template", holdout_type=HoldoutType.EXACT, holdout_value="c"
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
                axis_path="template", holdout_type=HoldoutType.EXACT, holdout_value="a"
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
                axis_path="template", holdout_type=HoldoutType.EXACT, holdout_value="a"
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
            AxisHoldout(axis_path="x", holdout_type=HoldoutType.EXACT, holdout_value=1),
            AxisHoldout(
                axis_path="y", holdout_type=HoldoutType.RANGE, holdout_value=(0, 10)
            ),
        ]
        result = split_tasks(tasks, holdouts)

        assert result.holdouts == holdouts
        assert len(result.holdouts) == 2
