"""Tests for difficulty-targeted presets."""

import random
from collections import Counter

import pytest

from genfxn.core.presets import (
    DifficultyPreset,
    PIECEWISE_PRESETS,
    SIMPLE_ALGORITHMS_PRESETS,
    STATEFUL_PRESETS,
    STRINGRULES_PRESETS,
    get_difficulty_axes,
    get_difficulty_presets,
    get_valid_difficulties,
)
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stateful.models import StatefulAxes
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.models import StringRulesAxes
from genfxn.stringrules.task import generate_stringrules_task


class TestGetValidDifficulties:
    def test_piecewise_range(self) -> None:
        valid = get_valid_difficulties("piecewise")
        assert valid == [1, 2, 3, 4, 5]

    def test_stateful_range(self) -> None:
        valid = get_valid_difficulties("stateful")
        assert valid == [1, 2, 3]

    def test_simple_algorithms_range(self) -> None:
        valid = get_valid_difficulties("simple_algorithms")
        assert valid == [2, 3]

    def test_stringrules_range(self) -> None:
        valid = get_valid_difficulties("stringrules")
        assert valid == [1, 2, 3, 4]

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

    def test_variant_selects_specific_preset(self) -> None:
        axes_a = get_difficulty_axes("piecewise", 3, variant="3A")
        axes_b = get_difficulty_axes("piecewise", 3, variant="3B")
        # Different variants should have different configurations
        assert axes_a.expr_types != axes_b.expr_types or axes_a.n_branches != axes_b.n_branches

    def test_invalid_variant_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid variant"):
            get_difficulty_axes("piecewise", 3, variant="3Z")

    def test_random_selection_with_rng(self) -> None:
        rng = random.Random(42)
        axes1 = get_difficulty_axes("piecewise", 3, rng=rng)
        rng = random.Random(42)
        axes2 = get_difficulty_axes("piecewise", 3, rng=rng)
        # Same seed should give same result
        assert axes1.n_branches == axes2.n_branches
        assert axes1.expr_types == axes2.expr_types


class TestPresetAccuracy:
    """Test that presets produce tasks at expected difficulty levels."""

    N_SAMPLES = 50
    EXACT_THRESHOLD = 0.70  # >70% should hit exact target
    WITHIN_ONE_THRESHOLD = 0.90  # >90% should be within ±1

    # Edge difficulties at family boundaries may have lower accuracy
    # due to formula constraints (e.g., stringrules max is ~3.8)
    EDGE_DIFFICULTIES = {
        ("stringrules", 4),  # Max achievable is ~3.8
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
                task = generate_piecewise_task(axes=axes, rng=rng)
            elif family == "stateful":
                task = generate_stateful_task(axes=axes, rng=rng)
            elif family == "simple_algorithms":
                task = generate_simple_algorithms_task(axes=axes, rng=rng)
            elif family == "stringrules":
                task = generate_stringrules_task(axes=axes, rng=rng)
            else:
                raise ValueError(f"Unknown family: {family}")

            difficulties.append(task.difficulty)

        return difficulties

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4, 5])
    def test_piecewise_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("piecewise", difficulty)
        self._verify_accuracy(difficulties, difficulty, "piecewise")

    @pytest.mark.parametrize("difficulty", [1, 2, 3])
    def test_stateful_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("stateful", difficulty)
        self._verify_accuracy(difficulties, difficulty, "stateful")

    @pytest.mark.parametrize("difficulty", [2, 3])
    def test_simple_algorithms_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("simple_algorithms", difficulty)
        self._verify_accuracy(difficulties, difficulty, "simple_algorithms")

    @pytest.mark.parametrize("difficulty", [1, 2, 3, 4])
    def test_stringrules_preset_accuracy(self, difficulty: int) -> None:
        difficulties = self._generate_tasks_for_preset("stringrules", difficulty)
        self._verify_accuracy(difficulties, difficulty, "stringrules")

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
        exact_threshold = self.EDGE_EXACT_THRESHOLD if is_edge else self.EXACT_THRESHOLD

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
            f"{family} difficulty {target}: only {within_one_ratio:.0%} within ±1 "
            f"(need {self.WITHIN_ONE_THRESHOLD:.0%}). Distribution: {dist_str}"
        )


class TestPresetVariety:
    """Test that different variants produce meaningfully different tasks."""

    def test_piecewise_variants_differ(self) -> None:
        presets_3 = get_difficulty_presets("piecewise", 3)
        assert len(presets_3) >= 2, "Need multiple variants to test variety"

        axes_a = get_difficulty_axes("piecewise", 3, variant=presets_3[0].name)
        axes_b = get_difficulty_axes("piecewise", 3, variant=presets_3[1].name)

        # At least one axis should differ
        differs = (
            axes_a.n_branches != axes_b.n_branches
            or axes_a.expr_types != axes_b.expr_types
            or axes_a.coeff_range != axes_b.coeff_range
        )
        assert differs, "Different variants should have different configurations"

    def test_stringrules_variants_differ(self) -> None:
        presets_2 = get_difficulty_presets("stringrules", 2)
        if len(presets_2) < 2:
            pytest.skip("Need multiple variants to test variety")

        axes_a = get_difficulty_axes("stringrules", 2, variant=presets_2[0].name)
        axes_b = get_difficulty_axes("stringrules", 2, variant=presets_2[1].name)

        differs = (
            axes_a.n_rules != axes_b.n_rules
            or axes_a.predicate_types != axes_b.predicate_types
            or axes_a.transform_types != axes_b.transform_types
        )
        assert differs, "Different variants should have different configurations"


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
            assert 1 <= difficulty <= 3
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_simple_algorithms_presets_structure(self) -> None:
        for difficulty, presets in SIMPLE_ALGORITHMS_PRESETS.items():
            assert isinstance(difficulty, int)
            assert difficulty in (2, 3)
            assert len(presets) >= 1
            for preset in presets:
                assert preset.name.startswith(f"{difficulty}")

    def test_stringrules_presets_structure(self) -> None:
        for difficulty, presets in STRINGRULES_PRESETS.items():
            assert isinstance(difficulty, int)
            assert 1 <= difficulty <= 4
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
        ]:
            for difficulty, presets in preset_dict.items():
                for preset in presets:
                    # Should not raise validation errors
                    axes = get_difficulty_axes(family, difficulty, variant=preset.name)
                    assert axes is not None
