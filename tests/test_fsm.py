import random

import pytest

from genfxn.core.predicates import (
    PredicateEven,
    PredicateLt,
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
from genfxn.fsm.render import render_fsm
from genfxn.fsm.sampler import sample_fsm_spec
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
        assert 1 <= task.difficulty <= 5
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
