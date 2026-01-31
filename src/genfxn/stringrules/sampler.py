import random
import string

from genfxn.core.string_predicates import (
    StringPredicate,
    StringPredicateContains,
    StringPredicateEndsWith,
    StringPredicateIsAlpha,
    StringPredicateIsDigit,
    StringPredicateIsLower,
    StringPredicateIsUpper,
    StringPredicateLengthCmp,
    StringPredicateStartsWith,
    StringPredicateType,
)
from genfxn.core.string_transforms import (
    StringTransform,
    StringTransformAppend,
    StringTransformCapitalize,
    StringTransformIdentity,
    StringTransformLowercase,
    StringTransformPrepend,
    StringTransformReplace,
    StringTransformReverse,
    StringTransformStrip,
    StringTransformSwapcase,
    StringTransformType,
    StringTransformUppercase,
)
from genfxn.core.trace import TraceStep
from genfxn.stringrules.models import (
    OverlapLevel,
    StringRule,
    StringRulesAxes,
    StringRulesSpec,
)


def _get_charset(name: str) -> str:
    charsets = {
        "ascii_letters_digits": string.ascii_letters + string.digits,
        "ascii_lowercase": string.ascii_lowercase,
        "ascii_uppercase": string.ascii_uppercase,
        "digits": string.digits,
        "ascii_letters": string.ascii_letters,
    }
    return charsets.get(name, name)


def _random_string(length: int, charset: str, rng: random.Random) -> str:
    return "".join(rng.choice(charset) for _ in range(length))


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


def sample_stringrules_spec(
    axes: StringRulesAxes,
    rng: random.Random | None = None,
    trace: list[TraceStep] | None = None,
) -> StringRulesSpec:
    if rng is None:
        rng = random.Random()

    if trace is not None:
        trace.append(
            TraceStep(
                step="sample_n_rules",
                choice=f"Number of rules: {axes.n_rules}",
                value=axes.n_rules,
            )
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

        if trace is not None:
            trace.append(
                TraceStep(
                    step=f"sample_rule_{i}_predicate",
                    choice=f"Rule {i} predicate: {pred_type.value}",
                    value=predicate.model_dump(),
                )
            )

        trans_type = rng.choice(axes.transform_types)
        transform = sample_string_transform(trans_type, axes, rng)

        if trace is not None:
            trace.append(
                TraceStep(
                    step=f"sample_rule_{i}_transform",
                    choice=f"Rule {i} transform: {trans_type.value}",
                    value=transform.model_dump(),
                )
            )

        rules.append(StringRule(predicate=predicate, transform=transform))

    # Sample default transform
    default_trans_type = rng.choice(axes.transform_types)
    default_transform = sample_string_transform(default_trans_type, axes, rng)

    if trace is not None:
        trace.append(
            TraceStep(
                step="sample_default_transform",
                choice=f"Default transform: {default_trans_type.value}",
                value=default_transform.model_dump(),
            )
        )

    return StringRulesSpec(rules=rules, default_transform=default_transform)
