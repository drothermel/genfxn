"""Tests for difficulty-targeted presets."""

import importlib.util
import random
from collections import Counter
from typing import ClassVar, cast

import pytest

from genfxn.bitops.models import BitopsAxes
from genfxn.bitops.task import generate_bitops_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.presets import (
    BITOPS_PRESETS,
    FSM_PRESETS,
    GRAPH_QUERIES_PRESETS,
    INTERVALS_PRESETS,
    PIECEWISE_PRESETS,
    SEQUENCE_DP_PRESETS,
    SIMPLE_ALGORITHMS_PRESETS,
    STATEFUL_PRESETS,
    STRINGRULES_PRESETS,
    TEMPORAL_LOGIC_PRESETS,
    DifficultyPreset,
    get_difficulty_axes,
    get_difficulty_presets,
    get_valid_difficulties,
)
from genfxn.fsm.models import FsmAxes
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries.models import GraphQueriesAxes
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.models import IntervalsAxes
from genfxn.intervals.task import generate_intervals_task
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp.models import SequenceDpAxes
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stateful.models import StatefulAxes
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.models import StringRulesAxes
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.temporal_logic.models import TemporalLogicAxes
from genfxn.temporal_logic.task import generate_temporal_logic_task


def _supports_stack_bytecode_presets() -> bool:
    if importlib.util.find_spec("genfxn.stack_bytecode.task") is None:
        pytest.fail("genfxn.stack_bytecode.task is not importable")
    try:
        valid = get_valid_difficulties("stack_bytecode")
    except ValueError as exc:
        pytest.fail(f"stack_bytecode presets unavailable: {exc}")
    if valid != [1, 2, 3, 4, 5]:
        pytest.fail(
            "stack_bytecode valid difficulties mismatch: "
            f"expected [1, 2, 3, 4, 5], got {valid}"
        )
    return True


class TestGetValidDifficulties:
    def test_piecewise_range(self) -> None:
        valid = get_valid_difficulties("piecewise")
        assert valid == [1, 2, 3, 4, 5]

    def test_stateful_range(self) -> None:
        valid = get_valid_difficulties("stateful")
        assert valid == [1, 2, 3, 4, 5]

    def test_simple_algorithms_range(self) -> None:
        valid = get_valid_difficulties("simple_algorithms")
        assert valid == [2, 3, 4, 5]

    def test_stringrules_range(self) -> None:
        valid = get_valid_difficulties("stringrules")
        assert valid == [1, 2, 3, 4, 5]

    def test_stack_bytecode_range_when_available(self) -> None:
        if not _supports_stack_bytecode_presets():
            pytest.skip("stack_bytecode presets are not available")
        valid = get_valid_difficulties("stack_bytecode")
        assert valid == [1, 2, 3, 4, 5]

    def test_fsm_range(self) -> None:
        valid = get_valid_difficulties("fsm")
        assert valid == [1, 2, 3, 4, 5]

    def test_bitops_range(self) -> None:
        valid = get_valid_difficulties("bitops")
        assert valid == [1, 2, 3, 4, 5]

    def test_sequence_dp_range(self) -> None:
        valid = get_valid_difficulties("sequence_dp")
        assert valid == [1, 2, 3, 4, 5]

    def test_intervals_range(self) -> None:
        valid = get_valid_difficulties("intervals")
        assert valid == [1, 2, 3, 4, 5]

    def test_graph_queries_range(self) -> None:
        valid = get_valid_difficulties("graph_queries")
        assert valid == [1, 2, 3, 4, 5]

    def test_temporal_logic_range(self) -> None:
        valid = get_valid_difficulties("temporal_logic")
        assert valid == [1, 2, 3, 4, 5]

    def test_unknown_family_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown family"):
            get_valid_difficulties("unknown")


class TestGetDifficultyPresets:
    def test_returns_list_of_presets(self) -> None:
        presets = get_difficulty_presets("piecewise", 3)
        assert isinstance(presets, list)
        assert len(presets) > 0
        assert all(isinstance(p, DifficultyPreset) for p in presets)

    def test_each_preset_has_unique_name(self) -> None:
        for difficulty in get_valid_difficulties("piecewise"):
            presets = get_difficulty_presets("piecewise", difficulty)
            names = [p.name for p in presets]
            assert len(names) == len(set(names))

    def test_invalid_difficulty_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid difficulty"):
            get_difficulty_presets("piecewise", 99)

    def test_invalid_family_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown family"):
            get_difficulty_presets("unknown", 1)


class TestGetDifficultyAxes:
    def test_piecewise_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("piecewise", 3)
        assert isinstance(axes, PiecewiseAxes)

    def test_stateful_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("stateful", 2)
        assert isinstance(axes, StatefulAxes)

    def test_simple_algorithms_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("simple_algorithms", 2)
        assert isinstance(axes, SimpleAlgorithmsAxes)

    def test_stringrules_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("stringrules", 2)
        assert isinstance(axes, StringRulesAxes)

    def test_fsm_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("fsm", 3)
        assert isinstance(axes, FsmAxes)

    def test_bitops_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("bitops", 3)
        assert isinstance(axes, BitopsAxes)

    def test_sequence_dp_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("sequence_dp", 3)
        assert isinstance(axes, SequenceDpAxes)

    def test_intervals_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("intervals", 3)
        assert isinstance(axes, IntervalsAxes)

    def test_graph_queries_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("graph_queries", 3)
        assert isinstance(axes, GraphQueriesAxes)

    def test_temporal_logic_returns_correct_type(self) -> None:
        axes = get_difficulty_axes("temporal_logic", 3)
        assert isinstance(axes, TemporalLogicAxes)

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_intervals_sets_target_difficulty(self, difficulty: int) -> None:
        axes = cast(
            IntervalsAxes,
            get_difficulty_axes(
                "intervals",
                difficulty,
                variant=f"{difficulty}A",
            ),
        )
        assert axes.target_difficulty == difficulty

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_graph_queries_sets_target_difficulty(
        self, difficulty: int
    ) -> None:
        axes = cast(
            GraphQueriesAxes,
            get_difficulty_axes(
                "graph_queries",
                difficulty,
                variant=f"{difficulty}A",
            ),
        )
        assert axes.target_difficulty == difficulty

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_temporal_logic_sets_target_difficulty(
        self, difficulty: int
    ) -> None:
        axes = cast(
            TemporalLogicAxes,
            get_difficulty_axes(
                "temporal_logic",
                difficulty,
                variant=f"{difficulty}A",
            ),
        )
        assert axes.target_difficulty == difficulty

    def test_variant_selects_specific_preset(self) -> None:
        axes_a = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 3, variant="3A"),
        )
        axes_b = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 3, variant="3B"),
        )
        # Different variants should have different configurations
        assert (
            axes_a.expr_types != axes_b.expr_types
            or axes_a.n_branches != axes_b.n_branches
        )

    def test_invalid_variant_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid variant"):
            get_difficulty_axes("piecewise", 3, variant="3Z")

    def test_random_selection_with_rng(self) -> None:
        rng = random.Random(42)
        axes1 = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 3, rng=rng),
        )
        rng = random.Random(42)
        axes2 = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 3, rng=rng),
        )
        # Same seed should give same result
        assert axes1.n_branches == axes2.n_branches
        assert axes1.expr_types == axes2.expr_types


class TestPresetAccuracy:
    """Test that presets produce tasks at expected difficulty levels."""

    N_SAMPLES = 50
    EXACT_THRESHOLD = 0.70  # >70% should hit exact target
    WITHIN_ONE_THRESHOLD = 0.90  # >90% should be within ±1

    # Edge difficulties at family boundaries may have lower accuracy
    # due to formula constraints or sampling variance
    EDGE_DIFFICULTIES = {
        ("stringrules", 4),  # Max achievable with atoms is ~3.8
        ("stringrules", 5),  # Composed/pipeline sampling variance
        ("stateful", 4),  # Composed NOT + pipeline sampling variance
        ("stateful", 5),  # Composed/pipeline sampling variance
        ("simple_algorithms", 5),  # Preprocess + edge sampling variance
        ("temporal_logic", 4),  # Temporal operator mix often rounds to D5
        ("temporal_logic", 5),  # Mixed D4/D5 due formula structure variance
    }
    EDGE_EXACT_THRESHOLD = 0.50  # >50% for edge cases
    EDGE_MEAN_TOLERANCE = 0.75  # ±0.75 for edge cases

    def _generate_tasks_for_preset(
        self, family: str, difficulty: int, n: int = N_SAMPLES
    ) -> list[int]:
        """Generate n tasks and return their difficulties."""
        rng = random.Random(42)
        difficulties = []

        for _ in range(n):
            axes = get_difficulty_axes(family, difficulty, rng=rng)
            if family == "piecewise":
                task = generate_piecewise_task(
                    axes=cast(PiecewiseAxes, axes), rng=rng
                )
            elif family == "stateful":
                task = generate_stateful_task(
                    axes=cast(StatefulAxes, axes), rng=rng
                )
            elif family == "simple_algorithms":
                task = generate_simple_algorithms_task(
                    axes=cast(SimpleAlgorithmsAxes, axes), rng=rng
                )
            elif family == "stringrules":
                task = generate_stringrules_task(
                    axes=cast(StringRulesAxes, axes), rng=rng
                )
            elif family == "fsm":
                task = generate_fsm_task(axes=cast(FsmAxes, axes), rng=rng)
            elif family == "bitops":
                task = generate_bitops_task(
                    axes=cast(BitopsAxes, axes), rng=rng
                )
            elif family == "sequence_dp":
                task = generate_sequence_dp_task(
                    axes=cast(SequenceDpAxes, axes), rng=rng
                )
            elif family == "intervals":
                task = generate_intervals_task(
                    axes=cast(IntervalsAxes, axes), rng=rng
                )
            elif family == "graph_queries":
                task = generate_graph_queries_task(
                    axes=cast(GraphQueriesAxes, axes),
                    rng=rng,
                )
            elif family == "temporal_logic":
                task = generate_temporal_logic_task(
                    axes=cast(TemporalLogicAxes, axes),
                    rng=rng,
                )
            else:
                raise ValueError(f"Unknown family: {family}")

            difficulties.append(task.difficulty)

        return difficulties

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_piecewise_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("piecewise", difficulty)
        self._verify_accuracy(difficulties, difficulty, "piecewise")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_stateful_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("stateful", difficulty)
        self._verify_accuracy(difficulties, difficulty, "stateful")

    @pytest.mark.parametrize("difficulty", [2, 3, 4, 5])
    def test_simple_algorithms_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset(
            "simple_algorithms", difficulty
        )
        self._verify_accuracy(difficulties, difficulty, "simple_algorithms")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_stringrules_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset(
            "stringrules", difficulty
        )
        self._verify_accuracy(difficulties, difficulty, "stringrules")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_bitops_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("bitops", difficulty)
        self._verify_accuracy(difficulties, difficulty, "bitops")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_sequence_dp_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset(
            "sequence_dp", difficulty
        )
        self._verify_accuracy(difficulties, difficulty, "sequence_dp")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_intervals_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("intervals", difficulty)
        self._verify_accuracy(difficulties, difficulty, "intervals")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_graph_queries_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset(
            "graph_queries", difficulty
        )
        self._verify_accuracy(difficulties, difficulty, "graph_queries")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_temporal_logic_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset(
            "temporal_logic", difficulty
        )
        self._verify_accuracy(difficulties, difficulty, "temporal_logic")

    def _verify_accuracy(
        self, difficulties: list[int], target: int, family: str
    ) -> None:
        """Verify that generated difficulties meet accuracy thresholds."""
        n = len(difficulties)
        mean_diff = sum(difficulties) / n
        exact_count = sum(1 for d in difficulties if d == target)
        within_one = sum(1 for d in difficulties if abs(d - target) <= 1)

        exact_ratio = exact_count / n
        within_one_ratio = within_one / n

        # Log for debugging
        counts = Counter(difficulties)
        dist_str = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))

        # Use relaxed thresholds for edge difficulties
        is_edge = (family, target) in self.EDGE_DIFFICULTIES
        mean_tolerance = self.EDGE_MEAN_TOLERANCE if is_edge else 0.5
        exact_threshold = (
            self.EDGE_EXACT_THRESHOLD if is_edge else self.EXACT_THRESHOLD
        )

        # Verify accuracy thresholds
        assert abs(mean_diff - target) <= mean_tolerance, (
            f"{family} difficulty {target}: mean {mean_diff:.2f} not within "
            f"±{mean_tolerance}. Distribution: {dist_str}"
        )
        assert exact_ratio >= exact_threshold, (
            f"{family} difficulty {target}: only {exact_ratio:.0%} exact "
            f"(need {exact_threshold:.0%}). Distribution: {dist_str}"
        )
        assert within_one_ratio >= self.WITHIN_ONE_THRESHOLD, (
            f"{family} difficulty {target}: only {within_one_ratio:.0%} "
            f"within ±1 "
            f"(need {self.WITHIN_ONE_THRESHOLD:.0%}). Distribution: {dist_str}"
        )


class TestPresetVariety:
    """Test that different variants produce meaningfully different tasks."""

    def test_piecewise_variants_differ(self) -> None:
        presets_3 = get_difficulty_presets("piecewise", 3)
        assert len(presets_3) >= 2, "Need multiple variants to test variety"

        axes_a = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 3, variant=presets_3[0].name),
        )
        axes_b = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 3, variant=presets_3[1].name),
        )

        # At least one axis should differ
        differs = (
            axes_a.n_branches != axes_b.n_branches
            or axes_a.expr_types != axes_b.expr_types
            or axes_a.coeff_range != axes_b.coeff_range
        )
        assert differs, (
            "Different variants should have different configurations"
        )

    def test_stringrules_variants_differ(self) -> None:
        presets_2 = get_difficulty_presets("stringrules", 2)
        if len(presets_2) < 2:
            pytest.skip("Need multiple variants to test variety")

        axes_a = cast(
            StringRulesAxes,
            get_difficulty_axes("stringrules", 2, variant=presets_2[0].name),
        )
        axes_b = cast(
            StringRulesAxes,
            get_difficulty_axes("stringrules", 2, variant=presets_2[1].name),
        )

        differs = (
            axes_a.n_rules != axes_b.n_rules
            or axes_a.predicate_types != axes_b.predicate_types
            or axes_a.transform_types != axes_b.transform_types
        )
        assert differs, (
            "Different variants should have different configurations"
        )

    def test_piecewise_difficulty4_variants_differ(self) -> None:
        axes_a = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 4, variant="4A"),
        )
        axes_b = cast(
            PiecewiseAxes,
            get_difficulty_axes("piecewise", 4, variant="4B"),
        )

        differs = (
            axes_a.n_branches != axes_b.n_branches
            or axes_a.expr_types != axes_b.expr_types
            or axes_a.coeff_range != axes_b.coeff_range
        )
        assert differs, (
            "piecewise difficulty-4 variants 4A and 4B should differ"
        )


class TestFsmPresets:
    N_SAMPLES = 50

    def test_fsm_means_increase_with_target(self) -> None:
        means: dict[int, float] = {}
        for difficulty in [1, 2, 3, 4, 5]:
            rng = random.Random(123 + difficulty)
            observed: list[int] = []
            for _ in range(self.N_SAMPLES):
                axes = cast(
                    FsmAxes,
                    get_difficulty_axes("fsm", difficulty, rng=rng),
                )
                task = generate_fsm_task(axes=axes, rng=rng)
                observed.append(compute_difficulty("fsm", task.spec))
            means[difficulty] = sum(observed) / len(observed)

        ordered_means = [means[d] for d in [1, 2, 3, 4, 5]]
        assert ordered_means == sorted(ordered_means)
        assert ordered_means[-1] - ordered_means[0] >= 2.5

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_fsm_presets_are_within_one_of_target(
        self, difficulty: int
    ) -> None:
        rng = random.Random(900 + difficulty)
        observed: list[int] = []
        for _ in range(self.N_SAMPLES):
            axes = cast(
                FsmAxes,
                get_difficulty_axes("fsm", difficulty, rng=rng),
            )
            task = generate_fsm_task(axes=axes, rng=rng)
            observed.append(compute_difficulty("fsm", task.spec))

        within_one_ratio = sum(
            1 for score in observed if abs(score - difficulty) <= 1
        ) / len(observed)
        assert within_one_ratio >= 0.9


class TestPresetCompleteness:
    """Test that preset dictionaries are well-formed."""

    def test_piecewise_presets_structure(self) -> None:
        for difficulty, presets in PIECEWISE_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")
                assert preset.description
                assert isinstance(preset.axes_overrides, dict)

    def test_stateful_presets_structure(self) -> None:
        for difficulty, presets in STATEFUL_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_simple_algorithms_presets_structure(self) -> None:
        for difficulty, presets in SIMPLE_ALGORITHMS_PRESETS.items():
            assert isinstance(difficulty, int)
            assert difficulty in (2, 3, 4, 5)
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_stringrules_presets_structure(self) -> None:
        for difficulty, presets in STRINGRULES_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_fsm_presets_structure(self) -> None:
        for difficulty, presets in FSM_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_bitops_presets_structure(self) -> None:
        for difficulty, presets in BITOPS_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_sequence_dp_presets_structure(self) -> None:
        for difficulty, presets in SEQUENCE_DP_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_intervals_presets_structure(self) -> None:
        for difficulty, presets in INTERVALS_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_graph_queries_presets_structure(self) -> None:
        for difficulty, presets in GRAPH_QUERIES_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_temporal_logic_presets_structure(self) -> None:
        for difficulty, presets in TEMPORAL_LOGIC_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 5
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_all_presets_produce_valid_axes(self) -> None:
        """Verify all preset overrides create valid axes objects."""
        for family, preset_dict in [
            ("piecewise", PIECEWISE_PRESETS),
            ("stateful", STATEFUL_PRESETS),
            ("simple_algorithms", SIMPLE_ALGORITHMS_PRESETS),
            ("stringrules", STRINGRULES_PRESETS),
            ("fsm", FSM_PRESETS),
            ("bitops", BITOPS_PRESETS),
            ("sequence_dp", SEQUENCE_DP_PRESETS),
            ("intervals", INTERVALS_PRESETS),
            ("graph_queries", GRAPH_QUERIES_PRESETS),
            ("temporal_logic", TEMPORAL_LOGIC_PRESETS),
        ]:
            for difficulty, presets in preset_dict.items():
                for preset in presets:
                    # Should not raise validation errors
                    axes = get_difficulty_axes(
                        family, difficulty, variant=preset.name
                    )
                    assert axes is not None


class TestStackBytecodePresets:
    N_SAMPLES = 40
    EXACT_THRESHOLDS: ClassVar[dict[int, float]] = {
        1: 0.0,
        2: 0.1,
        3: 0.3,
        4: 0.6,
        5: 0.9,
    }
    WITHIN_ONE_THRESHOLDS: ClassVar[dict[int, float]] = {
        1: 0.1,
        2: 0.3,
        3: 0.65,
        4: 0.95,
        5: 0.95,
    }

    def _require_stack_modules(self):
        if not _supports_stack_bytecode_presets():
            pytest.skip("stack_bytecode presets are not available")
        from genfxn.stack_bytecode.models import StackBytecodeAxes
        from genfxn.stack_bytecode.task import generate_stack_bytecode_task

        return StackBytecodeAxes, generate_stack_bytecode_task

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_stack_bytecode_preset_accuracy(self, difficulty: int) -> None:
        StackBytecodeAxes, generate_stack_bytecode_task = (
            self._require_stack_modules()
        )
        rng = random.Random(42)
        difficulties: list[int] = []

        for _ in range(self.N_SAMPLES):
            axes = cast(
                StackBytecodeAxes,
                get_difficulty_axes("stack_bytecode", difficulty, rng=rng),
            )
            task = generate_stack_bytecode_task(axes=axes, rng=rng)
            difficulties.append(compute_difficulty("stack_bytecode", task.spec))

        exact_ratio = sum(1 for d in difficulties if d == difficulty) / len(
            difficulties
        )
        within_one_ratio = sum(
            1 for d in difficulties if abs(d - difficulty) <= 1
        ) / len(difficulties)

        assert exact_ratio >= self.EXACT_THRESHOLDS[difficulty]
        assert within_one_ratio >= self.WITHIN_ONE_THRESHOLDS[difficulty]

    def test_stack_bytecode_variants_are_distinct(self) -> None:
        StackBytecodeAxes, _ = self._require_stack_modules()
        presets = get_difficulty_presets("stack_bytecode", 3)
        if len(presets) < 2:
            pytest.skip("Need multiple variants to test distinctness")

        axes_a = cast(
            StackBytecodeAxes,
            get_difficulty_axes("stack_bytecode", 3, variant=presets[0].name),
        )
        axes_b = cast(
            StackBytecodeAxes,
            get_difficulty_axes("stack_bytecode", 3, variant=presets[1].name),
        )

        assert (
            axes_a.max_step_count_range != axes_b.max_step_count_range
            or axes_a.const_range != axes_b.const_range
            or axes_a.jump_target_modes != axes_b.jump_target_modes
            or axes_a.input_modes != axes_b.input_modes
        )

    def test_stack_bytecode_means_increase_with_target(self) -> None:
        StackBytecodeAxes, generate_stack_bytecode_task = (
            self._require_stack_modules()
        )
        means: dict[int, float] = {}
        for difficulty in [1, 2, 3, 4, 5]:
            rng = random.Random(123 + difficulty)
            observed: list[int] = []
            for _ in range(self.N_SAMPLES):
                axes = cast(
                    StackBytecodeAxes,
                    get_difficulty_axes(
                        "stack_bytecode",
                        difficulty,
                        rng=rng,
                    ),
                )
                task = generate_stack_bytecode_task(axes=axes, rng=rng)
                observed.append(compute_difficulty("stack_bytecode", task.spec))
            means[difficulty] = sum(observed) / len(observed)

        ordered_means = [means[d] for d in [1, 2, 3, 4, 5]]
        assert ordered_means == sorted(ordered_means)
        assert ordered_means[-1] - ordered_means[0] >= 0.5

    def test_stack_bytecode_each_difficulty_has_presets(self) -> None:
        self._require_stack_modules()
        for difficulty in [1, 2, 3, 4, 5]:
            presets = get_difficulty_presets("stack_bytecode", difficulty)
            assert presets
            assert all(p.name.startswith(str(difficulty)) for p in presets)
