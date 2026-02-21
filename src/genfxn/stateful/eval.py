from genfxn.core.predicates import eval_predicate
from genfxn.core.transforms import eval_transform
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulSpec,
    ToggleSumSpec,
)


def _require_int_values_not_bool(xs: list[int], name: str) -> None:
    for index, value in enumerate(xs):
        if type(value) is not int:
            raise ValueError(
                f"{name}[{index}] must be int, got {type(value).__name__}"
            )


def eval_conditional_linear_sum(
    spec: ConditionalLinearSumSpec,
    xs: list[int],
) -> int:
    _require_int_values_not_bool(xs, "xs")
    acc = spec.init_value
    for x in xs:
        if eval_predicate(spec.predicate, x):
            transformed = eval_transform(spec.true_transform, x)
            acc = acc + transformed
        else:
            transformed = eval_transform(spec.false_transform, x)
            acc = acc + transformed
    return acc


def eval_resetting_best_prefix_sum(
    spec: ResettingBestPrefixSumSpec,
    xs: list[int],
) -> int:
    _require_int_values_not_bool(xs, "xs")
    init = spec.init_value
    current_sum = init
    best_sum = init
    for x in xs:
        if eval_predicate(spec.reset_predicate, x):
            current_sum = init
        else:
            val = (
                eval_transform(spec.value_transform, x)
                if spec.value_transform is not None
                else x
            )
            current_sum = current_sum + val
            best_sum = max(best_sum, current_sum)
    return best_sum


def eval_longest_run(
    spec: LongestRunSpec,
    xs: list[int],
) -> int:
    _require_int_values_not_bool(xs, "xs")
    current_run = 0
    longest_run = 0
    for x in xs:
        if eval_predicate(spec.match_predicate, x):
            current_run = current_run + 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 0
    return longest_run


def eval_toggle_sum(
    spec: ToggleSumSpec,
    xs: list[int],
) -> int:
    _require_int_values_not_bool(xs, "xs")
    on = False
    acc = spec.init_value
    for x in xs:
        if eval_predicate(spec.toggle_predicate, x):
            on = not on
        if on:
            transformed = eval_transform(spec.on_transform, x)
            acc = acc + transformed
        else:
            transformed = eval_transform(spec.off_transform, x)
            acc = acc + transformed
    return acc


def eval_stateful(
    spec: StatefulSpec,
    xs: list[int],
) -> int:
    match spec:
        case ConditionalLinearSumSpec():
            return eval_conditional_linear_sum(spec, xs)
        case ResettingBestPrefixSumSpec():
            return eval_resetting_best_prefix_sum(spec, xs)
        case LongestRunSpec():
            return eval_longest_run(spec, xs)
        case ToggleSumSpec():
            return eval_toggle_sum(spec, xs)
        case _:
            raise ValueError(f"Unknown stateful spec: {spec}")
