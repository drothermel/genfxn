import random
from typing import cast

from genfxn.core.string_predicates import (
    StringPredicate,
    StringPredicateAnd,
    StringPredicateAtom,
    StringPredicateContains,
    StringPredicateEndsWith,
    StringPredicateIsAlpha,
    StringPredicateIsDigit,
    StringPredicateIsLower,
    StringPredicateIsUpper,
    StringPredicateLengthCmp,
    StringPredicateNot,
    StringPredicateOr,
    StringPredicateStartsWith,
    StringPredicateType,
)
from genfxn.core.string_transforms import (
    StringTransform,
    StringTransformAppend,
    StringTransformAtom,
    StringTransformCapitalize,
    StringTransformIdentity,
    StringTransformLowercase,
    StringTransformPipeline,
    StringTransformPrepend,
    StringTransformReplace,
    StringTransformReverse,
    StringTransformStrip,
    StringTransformSwapcase,
    StringTransformType,
    StringTransformUppercase,
)
from genfxn.core.trace import TraceStep, trace_step
from genfxn.stringrules.models import (
    OverlapLevel,
    StringRule,
    StringRulesAxes,
    StringRulesSpec,
)
from genfxn.stringrules.utils import _get_charset, _random_string

_COMPOSED_PREDICATE_TYPES = {
    StringPredicateType.NOT,
    StringPredicateType.AND,
    StringPredicateType.OR,
}

_ATOMIC_PREDICATE_TYPES = [
    StringPredicateType.STARTS_WITH,
    StringPredicateType.ENDS_WITH,
    StringPredicateType.CONTAINS,
    StringPredicateType.IS_ALPHA,
    StringPredicateType.IS_DIGIT,
    StringPredicateType.IS_UPPER,
    StringPredicateType.IS_LOWER,
    StringPredicateType.LENGTH_CMP,
]

_ATOMIC_TRANSFORM_TYPES = [
    StringTransformType.IDENTITY,
    StringTransformType.LOWERCASE,
    StringTransformType.UPPERCASE,
    StringTransformType.CAPITALIZE,
    StringTransformType.SWAPCASE,
    StringTransformType.REVERSE,
    StringTransformType.REPLACE,
    StringTransformType.STRIP,
    StringTransformType.PREPEND,
    StringTransformType.APPEND,
]

_PARAMETERIZED_TRANSFORM_TYPES = [
    StringTransformType.REPLACE,
    StringTransformType.STRIP,
    StringTransformType.PREPEND,
    StringTransformType.APPEND,
]


def _sample_atomic_predicate_type(
    axes: StringRulesAxes, rng: random.Random
) -> StringPredicateType:
    atom_types = [
        t for t in axes.predicate_types if t not in _COMPOSED_PREDICATE_TYPES
    ]
    if not atom_types:
        atom_types = _ATOMIC_PREDICATE_TYPES
    return rng.choice(atom_types)


def _sample_pipeline_step_types(
    axes: StringRulesAxes, n_steps: int, rng: random.Random
) -> list[StringTransformType]:
    atom_types = [
        t for t in axes.transform_types if t != StringTransformType.PIPELINE
    ]
    if atom_types:
        return [rng.choice(atom_types) for _ in range(n_steps)]

    # Pipeline-only configs still need meaningful internal step variety.
    first = rng.choice(_PARAMETERIZED_TRANSFORM_TYPES)
    rest = [rng.choice(_ATOMIC_TRANSFORM_TYPES) for _ in range(n_steps - 1)]
    steps = [first, *rest]
    rng.shuffle(steps)
    return steps


def sample_string_predicate(
    pred_type: StringPredicateType,
    axes: StringRulesAxes,
    rng: random.Random,
) -> StringPredicate:
    charset = _get_charset(axes.charset)

    match pred_type:
        case StringPredicateType.STARTS_WITH:
            length = rng.randint(*axes.prefix_suffix_length_range)
            prefix = _random_string(length, charset, rng)
            return StringPredicateStartsWith(prefix=prefix)

        case StringPredicateType.ENDS_WITH:
            length = rng.randint(*axes.prefix_suffix_length_range)
            suffix = _random_string(length, charset, rng)
            return StringPredicateEndsWith(suffix=suffix)

        case StringPredicateType.CONTAINS:
            length = rng.randint(*axes.substring_length_range)
            substring = _random_string(length, charset, rng)
            return StringPredicateContains(substring=substring)

        case StringPredicateType.IS_ALPHA:
            return StringPredicateIsAlpha()

        case StringPredicateType.IS_DIGIT:
            return StringPredicateIsDigit()

        case StringPredicateType.IS_UPPER:
            return StringPredicateIsUpper()

        case StringPredicateType.IS_LOWER:
            return StringPredicateIsLower()

        case StringPredicateType.LENGTH_CMP:
            op = rng.choice(["lt", "le", "gt", "ge", "eq"])
            value = rng.randint(*axes.length_threshold_range)
            return StringPredicateLengthCmp(op=op, value=value)

        case StringPredicateType.NOT:
            operand_type = _sample_atomic_predicate_type(axes, rng)
            operand = sample_string_predicate(operand_type, axes, rng)
            return StringPredicateNot(
                operand=cast(StringPredicateAtom, operand)
            )

        case StringPredicateType.AND:
            n = rng.choice([2, 3])
            operands = [
                cast(
                    StringPredicateAtom,
                    sample_string_predicate(
                        _sample_atomic_predicate_type(axes, rng),
                        axes,
                        rng,
                    ),
                )
                for _ in range(n)
            ]
            return StringPredicateAnd(operands=operands)

        case StringPredicateType.OR:
            n = rng.choice([2, 3])
            operands = [
                cast(
                    StringPredicateAtom,
                    sample_string_predicate(
                        _sample_atomic_predicate_type(axes, rng),
                        axes,
                        rng,
                    ),
                )
                for _ in range(n)
            ]
            return StringPredicateOr(operands=operands)

        case _:
            raise ValueError(f"Unknown predicate type: {pred_type}")


def sample_string_transform(
    trans_type: StringTransformType,
    axes: StringRulesAxes,
    rng: random.Random,
) -> StringTransform:
    charset = _get_charset(axes.charset)

    match trans_type:
        case StringTransformType.IDENTITY:
            return StringTransformIdentity()

        case StringTransformType.LOWERCASE:
            return StringTransformLowercase()

        case StringTransformType.UPPERCASE:
            return StringTransformUppercase()

        case StringTransformType.CAPITALIZE:
            return StringTransformCapitalize()

        case StringTransformType.SWAPCASE:
            return StringTransformSwapcase()

        case StringTransformType.REVERSE:
            return StringTransformReverse()

        case StringTransformType.REPLACE:
            old_len = rng.randint(1, 2)
            new_len = rng.randint(0, 2)
            old = _random_string(old_len, charset, rng)
            new = _random_string(new_len, charset, rng)
            return StringTransformReplace(old=old, new=new)

        case StringTransformType.STRIP:
            if rng.random() < 0.5:
                return StringTransformStrip(chars=None)
            strip_chars = "".join(rng.sample(" \t\n_-", k=rng.randint(1, 3)))
            return StringTransformStrip(chars=strip_chars)

        case StringTransformType.PREPEND:
            length = rng.randint(*axes.prefix_suffix_length_range)
            prefix = _random_string(length, charset, rng)
            return StringTransformPrepend(prefix=prefix)

        case StringTransformType.APPEND:
            length = rng.randint(*axes.prefix_suffix_length_range)
            suffix = _random_string(length, charset, rng)
            return StringTransformAppend(suffix=suffix)

        case StringTransformType.PIPELINE:
            n = rng.choice([2, 3])
            step_types = _sample_pipeline_step_types(axes, n, rng)
            steps = [
                cast(
                    StringTransformAtom,
                    sample_string_transform(step_type, axes, rng),
                )
                for step_type in step_types
            ]
            return StringTransformPipeline(steps=steps)

        case _:
            raise ValueError(f"Unknown transform type: {trans_type}")


def _should_overlap(overlap_level: OverlapLevel, rng: random.Random) -> bool:
    """Decide if a new predicate should overlap with previous ones."""
    match overlap_level:
        case OverlapLevel.NONE:
            return False
        case OverlapLevel.LOW:
            return rng.random() < 0.2
        case OverlapLevel.HIGH:
            return rng.random() < 0.6
        case _:
            raise ValueError(
                f"Unknown OverlapLevel: {overlap_level!r}; expected one of "
                f"{list(OverlapLevel)}"
            )


def sample_stringrules_spec(
    axes: StringRulesAxes,
    rng: random.Random,
    trace: list[TraceStep] | None = None,
) -> StringRulesSpec:
    trace_step(
        trace,
        "sample_n_rules",
        f"Number of rules: {axes.n_rules}",
        axes.n_rules,
    )

    rules: list[StringRule] = []
    used_pred_types: set[StringPredicateType] = set()

    for i in range(axes.n_rules):
        # Select predicate type - avoid repeats unless overlapping
        available_types = list(axes.predicate_types)
        if not _should_overlap(axes.overlap_level, rng) and used_pred_types:
            available_types = [
                t for t in available_types if t not in used_pred_types
            ]
            if not available_types:
                available_types = list(axes.predicate_types)

        pred_type = rng.choice(available_types)
        used_pred_types.add(pred_type)

        predicate = sample_string_predicate(pred_type, axes, rng)

        # Track operand types for composed predicates to improve diversity
        if axes.overlap_level in (OverlapLevel.NONE, OverlapLevel.LOW):
            if isinstance(predicate, StringPredicateNot):
                used_pred_types.add(StringPredicateType(predicate.operand.kind))
            elif isinstance(predicate, (StringPredicateAnd, StringPredicateOr)):
                for op in predicate.operands:
                    used_pred_types.add(StringPredicateType(op.kind))

        trace_step(
            trace,
            f"sample_rule_{i}_predicate",
            f"Rule {i} predicate: {pred_type.value}",
            predicate.model_dump(),
        )

        trans_type = rng.choice(axes.transform_types)
        transform = sample_string_transform(trans_type, axes, rng)

        trace_step(
            trace,
            f"sample_rule_{i}_transform",
            f"Rule {i} transform: {trans_type.value}",
            transform.model_dump(),
        )

        rules.append(StringRule(predicate=predicate, transform=transform))

    # Sample default transform
    default_trans_type = rng.choice(axes.transform_types)
    default_transform = sample_string_transform(default_trans_type, axes, rng)

    trace_step(
        trace,
        "sample_default_transform",
        f"Default transform: {default_trans_type.value}",
        default_transform.model_dump(),
    )

    return StringRulesSpec(rules=rules, default_transform=default_transform)
