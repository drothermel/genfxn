"""Tests for balanced suite generation."""

import random

import pytest

from genfxn.simple_algorithms.models import TemplateType as SATemplateType
from genfxn.suites.features import (
    simple_algorithms_features,
    stateful_features,
    stringrules_features,
)
from genfxn.suites.generate import (
    Candidate,
    PoolStats,
    _pool_axes_simple_algorithms_d4,
    generate_pool,
    greedy_select,
)
from genfxn.suites.quotas import QUOTAS, Bucket, QuotaSpec

# ── Feature extraction tests ─────────────────────────────────────────────


class TestStringrulesFeatures:
    def test_simple_no_comp_no_pipe(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "lowercase"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "a"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "is_lower"},
                    "transform": {"kind": "capitalize"},
                },
            ],
            "default_transform": {"kind": "reverse"},
        }
        f = stringrules_features(spec)
        assert f["n_rules_bucket"] == "4-5"
        assert f["has_comp"] == "false"
        assert f["has_pipe"] == "false"
        assert f["mode"] == "neither"
        assert f["comp_max_score"] == "0"
        assert f["pipe_max_score"] == "0"
        assert f["pred_majority"] == "simple"  # 3 simple vs 1 pattern
        assert (
            f["transform_majority"] == "simple"
        )  # lowercase, uppercase, capitalize, reverse = 4 simple vs 1 identity

    def test_comp_only_mode(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {
                        "kind": "not",
                        "operand": {"kind": "is_alpha"},
                    },
                    "transform": {"kind": "lowercase"},
                },
                {
                    "predicate": {
                        "kind": "and",
                        "operands": [
                            {"kind": "is_digit"},
                            {"kind": "is_lower"},
                        ],
                    },
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "capitalize"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "x"},
                    "transform": {"kind": "reverse"},
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "lowercase"},
        }
        f = stringrules_features(spec)
        assert f["has_comp"] == "true"
        assert f["has_pipe"] == "false"
        assert f["mode"] == "comp-only"
        assert int(f["comp_max_score"]) >= 4

    def test_pipe_only_mode(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {
                        "kind": "pipeline",
                        "steps": [{"kind": "lowercase"}, {"kind": "reverse"}],
                    },
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_lower"},
                    "transform": {"kind": "capitalize"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "a"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "reverse"},
        }
        f = stringrules_features(spec)
        assert f["has_comp"] == "false"
        assert f["has_pipe"] == "true"
        assert f["mode"] == "pipe-only"
        assert int(f["pipe_max_score"]) >= 3

    def test_both_mode(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {
                        "kind": "not",
                        "operand": {"kind": "is_alpha"},
                    },
                    "transform": {
                        "kind": "pipeline",
                        "steps": [
                            {"kind": "lowercase"},
                            {"kind": "replace", "old": "a", "new": "b"},
                        ],
                    },
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_lower"},
                    "transform": {"kind": "capitalize"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "x"},
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "ends_with", "suffix": "y"},
                    "transform": {"kind": "reverse"},
                },
                {
                    "predicate": {"kind": "contains", "substring": "z"},
                    "transform": {"kind": "swapcase"},
                },
            ],
            "default_transform": {"kind": "lowercase"},
        }
        f = stringrules_features(spec)
        assert f["has_comp"] == "true"
        assert f["has_pipe"] == "true"
        assert f["mode"] == "both"
        assert f["n_rules_bucket"] == "6-7"

    def test_n_rules_buckets(self) -> None:
        def make_spec(n: int) -> dict:
            rules = [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "identity"},
                }
            ] * n
            return {"rules": rules, "default_transform": {"kind": "identity"}}

        assert stringrules_features(make_spec(4))["n_rules_bucket"] == "4-5"
        assert stringrules_features(make_spec(5))["n_rules_bucket"] == "4-5"
        assert stringrules_features(make_spec(6))["n_rules_bucket"] == "6-7"
        assert stringrules_features(make_spec(7))["n_rules_bucket"] == "6-7"
        assert stringrules_features(make_spec(8))["n_rules_bucket"] == "8-10"
        assert stringrules_features(make_spec(10))["n_rules_bucket"] == "8-10"


class TestStatefulFeatures:
    def test_conditional_comparison(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "gt", "value": 5},
            "true_transform": {"kind": "shift", "offset": 3},
            "false_transform": {"kind": "scale", "factor": 2},
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["template"] == "conditional_linear_sum"
        assert f["pred_kind"] == "comparison"
        assert f["transform_bucket"] == "atomic_nonidentity"
        assert f["transform_signature"] == "both_affine"

    def test_conditional_mixed_signature(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "mod_eq", "divisor": 3, "remainder": 0},
            "true_transform": {"kind": "abs"},
            "false_transform": {"kind": "shift", "offset": 1},
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["pred_kind"] == "mod_eq"
        assert f["transform_signature"] == "mixed"

    def test_conditional_sign_signature(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "lt", "value": 0},
            "true_transform": {"kind": "abs"},
            "false_transform": {"kind": "negate"},
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["transform_signature"] == "both_sign"

    def test_resetting_pipeline5(self) -> None:
        spec = {
            "template": "resetting_best_prefix_sum",
            "reset_predicate": {
                "kind": "and",
                "operands": [{"kind": "gt", "value": 0}, {"kind": "even"}],
            },
            "init_value": 0,
            "value_transform": {
                "kind": "pipeline",
                "steps": [
                    {"kind": "shift", "offset": 1},
                    {"kind": "scale", "factor": 2},
                    {"kind": "abs"},
                ],
            },
        }
        f = stateful_features(spec)
        assert f["template"] == "resetting_best_prefix_sum"
        assert f["pred_kind"] == "composed"
        assert f["transform_bucket"] == "pipeline5"
        assert "transform_signature" not in f  # only for conditional

    def test_toggle_sum(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {
                "kind": "mod_eq",
                "divisor": 2,
                "remainder": 0,
            },
            "on_transform": {
                "kind": "pipeline",
                "steps": [{"kind": "shift", "offset": 5}, {"kind": "abs"}],
            },
            "off_transform": {
                "kind": "pipeline",
                "steps": [{"kind": "scale", "factor": -1}, {"kind": "negate"}],
            },
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["template"] == "toggle_sum"
        assert f["pred_kind"] == "mod_eq"
        # pipeline with 1 param step → score 4
        assert f["transform_bucket"] == "pipeline4"


class TestSimpleAlgorithmsFeatures:
    def test_no_preprocess(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": -5,
            "counting_mode": "all_indices",
        }
        f = simple_algorithms_features(spec)
        assert f["template"] == "count_pairs_sum"
        assert f["preprocess_bucket"] == "none"
        assert f["has_filter"] == "false"
        assert f["has_transform"] == "false"
        assert f["filter_kind"] == "none"
        assert f["pre_transform_complexity"] == "none"
        assert f["edge_count"] == "0"
        assert f["target_sign"] == "neg"

    def test_with_preprocess_both(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
            "pre_filter": {"kind": "mod_eq", "divisor": 3, "remainder": 0},
            "pre_transform": {
                "kind": "pipeline",
                "steps": [
                    {"kind": "shift", "offset": 1},
                    {"kind": "scale", "factor": 2},
                ],
            },
            "tie_default": 99,
        }
        f = simple_algorithms_features(spec)
        assert f["preprocess_bucket"] == "both"
        assert f["has_filter"] == "true"
        assert f["has_transform"] == "true"
        assert f["filter_kind"] == "mod_eq"
        assert (
            f["pre_transform_complexity"] == "pipeline5"
        )  # 2 param steps → score 5
        assert f["edge_count"] == "1"  # tie_default

    def test_max_window_sum_edges(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 8,
            "invalid_k_default": 0,
            "pre_filter": {"kind": "gt", "value": 0},
            "pre_transform": {"kind": "abs"},
            "empty_default": -1,
        }
        f = simple_algorithms_features(spec)
        assert f["template"] == "max_window_sum"
        assert f["k_bucket"] == "8-10"
        assert f["preprocess_bucket"] == "both"
        assert f["filter_kind"] == "comparison"
        assert f["pre_transform_complexity"] == "atomic"
        assert f["edge_count"] == "1"  # empty_default

    def test_max_window_sum_k_bucket_out_of_range(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 5,
            "pre_filter": None,
            "pre_transform": None,
        }
        f = simple_algorithms_features(spec)
        assert f["k_bucket"] == "out_of_range"

    def test_target_sign_zero(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 0,
            "counting_mode": "unique_values",
        }
        f = simple_algorithms_features(spec)
        assert f["target_sign"] == "zero"

    def test_target_sign_pos(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "all_indices",
        }
        f = simple_algorithms_features(spec)
        assert f["target_sign"] == "pos"

    def test_filter_only(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 5,
            "counting_mode": "all_indices",
            "pre_filter": {
                "kind": "and",
                "operands": [
                    {"kind": "gt", "value": 0},
                    {"kind": "lt", "value": 100},
                ],
            },
            "no_result_default": -1,
        }
        f = simple_algorithms_features(spec)
        assert f["preprocess_bucket"] == "filter_only"
        assert f["filter_kind"] == "composed"
        assert f["edge_count"] == "1"


class _FixedChoiceRng:
    def __init__(self, choices: list[object]) -> None:
        self._choices = choices
        self._idx = 0

    def choice(self, options: list[object]) -> object:
        if self._idx >= len(self._choices):
            raise AssertionError(f"Unexpected choice call: {options!r}")

        picked = self._choices[self._idx]
        self._idx += 1
        assert picked in options, f"{picked!r} not in {options!r}"
        return picked


class TestSimpleAlgorithmsD4PoolAxes:
    def test_most_frequent_uses_only_tie_default_edge(self) -> None:
        rng = _FixedChoiceRng(
            [
                SATemplateType.MOST_FREQUENT,
                "comparison",
                "atomic",
            ]
        )

        axes = _pool_axes_simple_algorithms_d4(rng)

        assert axes.templates == [SATemplateType.MOST_FREQUENT]
        assert axes.tie_default_range == (-10, 10)
        assert axes.empty_default_range == (0, 0)
        assert axes.no_result_default_range is None
        assert axes.short_list_default_range is None

    def test_max_window_sum_uses_only_empty_default_edge(self) -> None:
        rng = _FixedChoiceRng(
            [
                SATemplateType.MAX_WINDOW_SUM,
                "filter_only",
                "comparison",
            ]
        )

        axes = _pool_axes_simple_algorithms_d4(rng)

        assert axes.templates == [SATemplateType.MAX_WINDOW_SUM]
        assert axes.empty_default_for_empty_range == (-10, 10)
        assert axes.window_size_range == (1, 10)
        assert axes.no_result_default_range is None
        assert axes.short_list_default_range is None

    def test_count_pairs_sum_can_enable_second_edge(self) -> None:
        rng = _FixedChoiceRng(
            [
                SATemplateType.COUNT_PAIRS_SUM,
                "filter_only",
                "comparison",
                2,
            ]
        )

        axes = _pool_axes_simple_algorithms_d4(rng)

        assert axes.templates == [SATemplateType.COUNT_PAIRS_SUM]
        assert axes.no_result_default_range == (-10, 10)
        assert axes.short_list_default_range == (-5, 5)


# ── Hard constraint filtering tests ──────────────────────────────────────


class TestHardConstraints:
    def test_stringrules_d3_filters(self) -> None:
        quota = QUOTAS["stringrules"][3]
        # Should pass: no comp, no pipe
        features_ok = {
            "has_comp": "false",
            "has_pipe": "false",
            "n_rules_bucket": "4-5",
        }
        # Should fail: has comp
        features_bad = {
            "has_comp": "true",
            "has_pipe": "false",
            "n_rules_bucket": "4-5",
        }

        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val
        assert any(
            features_bad.get(k) != v for k, v in quota.hard_constraints.items()
        )

    def test_simple_algorithms_d5_filters(self) -> None:
        quota = QUOTAS["simple_algorithms"][5]
        features_ok = {"preprocess_bucket": "both"}
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_stateful_d5_filters(self) -> None:
        quota = QUOTAS["stateful"][5]
        features_ok = {"transform_bucket": "pipeline5", "pred_kind": "composed"}
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val


# ── Greedy selection tests ───────────────────────────────────────────────


class TestGreedySelect:
    def _make_candidate(self, task_id: str, features: dict[str, str]) -> Candidate:
        return Candidate(spec=None, spec_dict={}, task_id=task_id, features=features)

    def test_simple_selection(self) -> None:
        """Small synthetic pool, verify greedy fills buckets."""
        quota = QuotaSpec(
            hard_constraints={},
            buckets=[
                Bucket("color", "red", 3),
                Bucket("color", "blue", 2),
            ],
            total=5,
        )

        candidates = []
        for i in range(10):
            color = "red" if i % 3 == 0 else "blue"
            candidates.append(self._make_candidate(f"id_{i}", {"color": color}))

        rng = random.Random(42)
        selected = greedy_select(candidates, quota, rng)
        assert len(selected) == 5

        red_count = sum(1 for c in selected if c.features["color"] == "red")
        blue_count = sum(1 for c in selected if c.features["color"] == "blue")
        assert red_count >= 3
        assert blue_count >= 2

    def test_hard_constraints_filter(self) -> None:
        """Hard constraints filter out non-matching candidates."""
        quota = QuotaSpec(
            hard_constraints={"shape": "circle"},
            buckets=[Bucket("color", "red", 2)],
            total=3,
        )

        candidates = [
            self._make_candidate("id_0", {"shape": "circle", "color": "red"}),
            self._make_candidate("id_1", {"shape": "square", "color": "red"}),
            self._make_candidate("id_2", {"shape": "circle", "color": "blue"}),
            self._make_candidate("id_3", {"shape": "circle", "color": "red"}),
        ]

        rng = random.Random(42)
        selected = greedy_select(candidates, quota, rng)
        # Only circles should be selected
        assert all(c.features["shape"] == "circle" for c in selected)
        assert len(selected) == 3

    def test_conditional_buckets(self) -> None:
        """Conditional buckets only count candidates matching conditions."""
        quota = QuotaSpec(
            hard_constraints={},
            buckets=[
                Bucket("shape", "circle", 2),
                Bucket("shape", "square", 2),
                Bucket("color", "red", 1, condition={"shape": "circle"}),
                Bucket("color", "blue", 1, condition={"shape": "circle"}),
            ],
            total=4,
        )

        candidates = [
            self._make_candidate("id_0", {"shape": "circle", "color": "red"}),
            self._make_candidate("id_1", {"shape": "circle", "color": "blue"}),
            self._make_candidate("id_2", {"shape": "circle", "color": "red"}),
            self._make_candidate("id_3", {"shape": "square", "color": "red"}),
            self._make_candidate("id_4", {"shape": "square", "color": "blue"}),
        ]

        rng = random.Random(42)
        selected = greedy_select(candidates, quota, rng)
        assert len(selected) == 4

        circles = [c for c in selected if c.features["shape"] == "circle"]
        squares = [c for c in selected if c.features["shape"] == "square"]
        assert len(circles) >= 2
        assert len(squares) >= 2


# ── Pool generation smoke test ───────────────────────────────────────────


class TestPoolGeneration:
    @pytest.mark.parametrize(
        "family,difficulty",
        [
            ("stringrules", 3),
            ("stringrules", 4),
            ("stringrules", 5),
            ("stateful", 3),
            ("stateful", 4),
            ("stateful", 5),
            ("simple_algorithms", 3),
            ("simple_algorithms", 4),
            ("simple_algorithms", 5),
        ],
    )
    def test_pool_generates_candidates(
        self, family: str, difficulty: int
    ) -> None:
        """Pool produces candidates at correct difficulty."""
        candidates, stats = generate_pool(family, difficulty, seed=42, pool_size=200)
        assert len(candidates) > 0, f"No candidates for {family} D{difficulty}"
        assert stats.candidates == len(candidates)
        assert stats.total_sampled == 200
        # All should have the right difficulty
        for cand in candidates:
            from genfxn.core.difficulty import compute_difficulty

            assert compute_difficulty(family, cand.spec_dict) == difficulty

    def test_pool_raises_after_too_many_sampling_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        def always_fail(
            _family: str, _axes: object, _rng: random.Random, trace: object = None,
        ) -> object:
            raise ValueError("forced sampler failure")

        monkeypatch.setattr(suite_generate, "_sample_spec", always_fail)

        with pytest.raises(RuntimeError, match="Sampling failed"):
            generate_pool("stateful", 3, seed=42, pool_size=50)


# ── Determinism test ─────────────────────────────────────────────────────


class TestDeterminism:
    def test_generate_suite_deterministic(self) -> None:
        """Same seed produces identical task_ids and queries across calls."""
        from genfxn.suites.generate import generate_suite

        a = generate_suite("stringrules", 3, seed=7, pool_size=500)
        b = generate_suite("stringrules", 3, seed=7, pool_size=500)

        assert len(a) == len(b) > 0
        for ta, tb in zip(a, b):
            assert ta.task_id == tb.task_id
            assert ta.queries == tb.queries

    def test_generate_suite_raises_when_quota_unfilled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        monkeypatch.setattr(
            suite_generate, "generate_pool", lambda *_: ([], PoolStats())
        )

        with pytest.raises(RuntimeError, match="Could not fill suite"):
            suite_generate.generate_suite(
                "stringrules", 3, seed=7, pool_size=20, max_retries=1
            )


# ── Integration test (marked slow) ──────────────────────────────────────


class TestIntegration:
    @pytest.mark.slow
    @pytest.mark.parametrize(
        "family,difficulty",
        [
            ("stringrules", 3),
            ("stateful", 3),
            ("simple_algorithms", 3),
        ],
    )
    def test_full_suite_generation(self, family: str, difficulty: int) -> None:
        """Full suite generation with quota checking."""
        from genfxn.suites.generate import generate_suite, quota_report

        tasks = generate_suite(family, difficulty, seed=42, pool_size=2000)
        assert len(tasks) == 50

        report = quota_report(tasks, family, difficulty)
        for axis, value, target, achieved, status in report:
            # Allow some slack (within 80% of target)
            min_acceptable = max(1, int(target * 0.8))
            assert achieved >= min_acceptable, (
                f"{family} D{difficulty}: {axis}={value} got {achieved}, "
                f"need >= {min_acceptable} (target={target})"
            )
