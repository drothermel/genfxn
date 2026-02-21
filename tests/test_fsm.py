import random

import pytest

from genfxn.core.models import QueryTag
from genfxn.core.predicates import (
    PredicateEven,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
)
from genfxn.fsm.eval import eval_fsm
from genfxn.fsm.models import (
    FsmAxes,
    FsmSpec,
    MachineType,
    OutputMode,
    PredicateType,
    State,
    Transition,
    UndefinedTransitionPolicy,
)
from genfxn.fsm.queries import generate_fsm_queries
from genfxn.fsm.render import render_fsm
from genfxn.fsm.sampler import _sample_predicate, sample_fsm_spec
from genfxn.fsm.task import generate_fsm_task


def _base_states() -> list[State]:
    return [
        State(
            id=0,
            is_accept=False,
            transitions=[
                Transition(predicate=PredicateEven(), target_state_id=1),
                Transition(predicate=PredicateLt(value=10), target_state_id=2),
            ],
        ),
        State(
            id=1,
            is_accept=True,
            transitions=[
                Transition(predicate=PredicateOdd(), target_state_id=0),
            ],
        ),
        State(id=2, is_accept=False, transitions=[]),
    ]


def _spec(
    *,
    machine_type: MachineType = MachineType.MOORE,
    output_mode: OutputMode = OutputMode.FINAL_STATE_ID,
    policy: UndefinedTransitionPolicy = UndefinedTransitionPolicy.STAY,
) -> FsmSpec:
    return FsmSpec(
        machine_type=machine_type,
        output_mode=output_mode,
        undefined_transition_policy=policy,
        start_state_id=0,
        states=_base_states(),
    )


class TestModels:
    def test_duplicate_state_ids_rejected(self) -> None:
        with pytest.raises(ValueError, match="state ids must be unique"):
            FsmSpec(
                machine_type=MachineType.MOORE,
                output_mode=OutputMode.FINAL_STATE_ID,
                undefined_transition_policy=UndefinedTransitionPolicy.STAY,
                start_state_id=0,
                states=[State(id=0), State(id=0)],
            )

    def test_transition_target_must_exist(self) -> None:
        with pytest.raises(ValueError, match="target_state_id"):
            FsmSpec(
                machine_type=MachineType.MOORE,
                output_mode=OutputMode.FINAL_STATE_ID,
                undefined_transition_policy=UndefinedTransitionPolicy.STAY,
                start_state_id=0,
                states=[
                    State(
                        id=0,
                        transitions=[
                            Transition(
                                predicate=PredicateEven(),
                                target_state_id=99,
                            )
                        ],
                    )
                ],
            )

    def test_state_id_rejects_values_that_overflow_sink_state(self) -> None:
        with pytest.raises(Exception, match="states.0.id"):
            FsmSpec.model_validate(
                {
                    "machine_type": "moore",
                    "output_mode": "final_state_id",
                    "undefined_transition_policy": "stay",
                    "start_state_id": 2_147_483_647,
                    "states": [
                        {
                            "id": 2_147_483_647,
                            "is_accept": False,
                            "transitions": [],
                        }
                    ],
                }
            )

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("n_states_range", (False, 3)),
            ("transitions_per_state_range", (0, True)),
            ("value_range", (False, 5)),
            ("threshold_range", (0, True)),
            ("divisor_range", (2, True)),
        ],
    )
    def test_axes_reject_bool_in_int_range_bounds(
        self, field_name: str, range_value: tuple[int | bool, int | bool]
    ) -> None:
        with pytest.raises(
            Exception,
            match=rf"{field_name}: bool is not allowed for int range bounds",
        ):
            FsmAxes.model_validate({field_name: range_value})

    def test_axes_reject_n_states_range_above_int32_max(self) -> None:
        with pytest.raises(Exception, match="n_states_range: high"):
            FsmAxes.model_validate({"n_states_range": (2, 2_147_483_648)})

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("value_range", (-(1 << 31) - 1, 0)),
            ("value_range", (0, (1 << 31))),
            ("threshold_range", (-(1 << 31) - 1, 0)),
            ("threshold_range", (0, (1 << 31))),
        ],
    )
    def test_axes_reject_ranges_outside_int32_contract(
        self, field_name: str, range_value: tuple[int, int]
    ) -> None:
        with pytest.raises(Exception, match=rf"{field_name}: .*fsm parity"):
            FsmAxes.model_validate({field_name: range_value})

    def test_spec_rejects_comparison_threshold_outside_int32_contract(
        self,
    ) -> None:
        with pytest.raises(Exception, match="signed 32-bit range"):
            FsmSpec.model_validate(
                {
                    "machine_type": "moore",
                    "output_mode": "final_state_id",
                    "undefined_transition_policy": "stay",
                    "start_state_id": 0,
                    "states": [
                        {
                            "id": 0,
                            "is_accept": False,
                            "transitions": [
                                {
                                    "predicate": {
                                        "kind": "lt",
                                        "value": 2_147_483_648,
                                    },
                                    "target_state_id": 0,
                                }
                            ],
                        }
                    ],
                }
            )


class TestEvaluatorSemantics:
    def test_ordered_transitions_first_match_wins(self) -> None:
        spec = _spec(output_mode=OutputMode.FINAL_STATE_ID)
        # x=4 matches both transitions at state 0, first (even->1) must win
        assert eval_fsm(spec, [4]) == 1

    def test_stay_policy_keeps_state_on_undefined_transition(self) -> None:
        spec = _spec(
            output_mode=OutputMode.FINAL_STATE_ID,
            policy=UndefinedTransitionPolicy.STAY,
        )
        # state 2 has no transitions, undefined with STAY should keep state 2
        assert eval_fsm(spec, [3, 11, 5]) == 2

    def test_sink_policy_moves_to_virtual_sink(self) -> None:
        spec = _spec(
            output_mode=OutputMode.FINAL_STATE_ID,
            policy=UndefinedTransitionPolicy.SINK,
        )
        # max declared state id is 2, sink must be 3
        assert eval_fsm(spec, [3, 11]) == 3

    def test_error_policy_raises_on_undefined_transition(self) -> None:
        spec = _spec(policy=UndefinedTransitionPolicy.ERROR)
        with pytest.raises(ValueError, match="undefined transition"):
            eval_fsm(spec, [3, 11])

    def test_accept_output_mode(self) -> None:
        spec = _spec(output_mode=OutputMode.ACCEPT_BOOL)
        assert eval_fsm(spec, [2]) == 1
        assert eval_fsm(spec, [3]) == 0

    def test_transition_count_counts_taken_or_sink_only(self) -> None:
        spec_stay = _spec(
            output_mode=OutputMode.TRANSITION_COUNT,
            policy=UndefinedTransitionPolicy.STAY,
        )
        # 0 --(3 lt10)--> 2 counts 1, then undefined in state 2 is STAY count 0
        assert eval_fsm(spec_stay, [3, 5, 7]) == 1

        spec_sink = _spec(
            output_mode=OutputMode.TRANSITION_COUNT,
            policy=UndefinedTransitionPolicy.SINK,
        )
        # 0->2 plus two sink transitions
        assert eval_fsm(spec_sink, [3, 5, 7]) == 3

    def test_mealy_machine_type_uses_same_deterministic_transition_order(
        self,
    ) -> None:
        spec = _spec(
            machine_type=MachineType.MEALY,
            output_mode=OutputMode.FINAL_STATE_ID,
        )
        assert eval_fsm(spec, [4, 5, 8]) == 1


class TestRenderParity:
    @pytest.mark.parametrize("machine_type", list(MachineType))
    @pytest.mark.parametrize(
        "policy",
        [UndefinedTransitionPolicy.STAY, UndefinedTransitionPolicy.SINK],
    )
    @pytest.mark.parametrize("output_mode", list(OutputMode))
    def test_rendered_python_matches_evaluator(
        self,
        machine_type: MachineType,
        policy: UndefinedTransitionPolicy,
        output_mode: OutputMode,
    ) -> None:
        spec = _spec(
            machine_type=machine_type,
            output_mode=output_mode,
            policy=policy,
        )
        code = render_fsm(spec)

        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]

        for xs in ([], [2], [3], [3, 11], [4, 5, 8], [3, 5, 7, 9]):
            assert f(xs) == eval_fsm(spec, xs)


class TestSampler:
    def test_sampler_is_deterministic_for_seed(self) -> None:
        axes = FsmAxes(
            n_states_range=(3, 3),
            transitions_per_state_range=(2, 2),
            predicate_types=[PredicateType.EVEN, PredicateType.GT],
        )

        spec1 = sample_fsm_spec(axes, random.Random(42))
        spec2 = sample_fsm_spec(axes, random.Random(42))
        assert spec1.model_dump() == spec2.model_dump()

    def test_sampler_varies_state_and_transition_shapes(self) -> None:
        axes = FsmAxes()
        specs = [
            sample_fsm_spec(axes, random.Random(1000 + i)) for i in range(24)
        ]
        signatures = {
            (
                len(spec.states),
                sum(len(state.transitions) for state in spec.states),
            )
            for spec in specs
        }
        assert len(signatures) >= 6

    def test_sampler_mod_eq_predicates_respect_divisor_range(self) -> None:
        axes = FsmAxes(
            predicate_types=[PredicateType.MOD_EQ],
            divisor_range=(2, 2),
            n_states_range=(2, 2),
            transitions_per_state_range=(1, 1),
        )
        spec = sample_fsm_spec(axes, random.Random(77))

        for state in spec.states:
            for transition in state.transitions:
                predicate = transition.predicate
                assert isinstance(predicate, PredicateModEq)
                assert predicate.divisor == 2
                assert 0 <= predicate.remainder < predicate.divisor

    def test_sample_predicate_unknown_type_raises(self) -> None:
        class _UnknownPredicateType:
            value = "unknown_new_pred"

        with pytest.raises(ValueError, match="unknown_new_pred"):
            _sample_predicate(
                _UnknownPredicateType(),  # type: ignore[arg-type]
                threshold_range=(-1, 1),
                divisor_range=(2, 3),
                rng=random.Random(1),
            )

    def test_sample_predicate_mod_eq_rejects_non_positive_divisor_range(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="divisor_range must include"):
            _sample_predicate(
                PredicateType.MOD_EQ,
                threshold_range=(-1, 1),
                divisor_range=(0, 0),
                rng=random.Random(1),
            )


class TestQueries:
    def test_queries_cover_all_tags_and_match_evaluator_outputs(self) -> None:
        axes = FsmAxes(
            value_range=(-7, 7),
            n_states_range=(3, 4),
            transitions_per_state_range=(1, 2),
        )
        spec = sample_fsm_spec(axes, random.Random(41))
        queries = generate_fsm_queries(spec, axes, random.Random(41))

        assert queries
        assert {q.tag for q in queries} == set(QueryTag)
        assert len({tuple(q.input) for q in queries}) == len(queries)
        for q in queries:
            assert q.output == eval_fsm(spec, q.input)


class TestTaskGeneration:
    def test_generate_fsm_task_wiring_and_query_outputs_match_eval(
        self,
    ) -> None:
        axes = FsmAxes(
            machine_types=[MachineType.MOORE],
            output_modes=[OutputMode.FINAL_STATE_ID],
            undefined_transition_policies=[UndefinedTransitionPolicy.STAY],
            predicate_types=[PredicateType.EVEN, PredicateType.LT],
            n_states_range=(3, 3),
            transitions_per_state_range=(1, 1),
            value_range=(-5, 5),
            threshold_range=(-2, 2),
            divisor_range=(2, 2),
        )
        task = generate_fsm_task(axes=axes, rng=random.Random(42))

        assert task.task_id
        assert task.family == "fsm"
        assert task.description

        spec = FsmSpec.model_validate(task.spec)
        assert task.queries
        for q in task.queries:
            assert q.output == eval_fsm(spec, q.input)

    def test_generate_fsm_task_is_deterministic_for_seed(self) -> None:
        axes = FsmAxes(
            machine_types=[MachineType.MOORE],
            output_modes=[OutputMode.FINAL_STATE_ID],
            undefined_transition_policies=[UndefinedTransitionPolicy.STAY],
            predicate_types=[PredicateType.EVEN, PredicateType.LT],
            n_states_range=(3, 3),
            transitions_per_state_range=(1, 1),
        )
        task1 = generate_fsm_task(axes=axes, rng=random.Random(42))
        task2 = generate_fsm_task(axes=axes, rng=random.Random(42))

        assert task1.model_dump() == task2.model_dump()
