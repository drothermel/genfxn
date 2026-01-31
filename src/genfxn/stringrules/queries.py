import random
import string

from genfxn.core.models import Query, QueryTag
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
    eval_string_predicate,
)
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import StringRulesAxes, StringRulesSpec


def _get_charset(name: str) -> str:
    charsets = {
        "ascii_letters_digits": string.ascii_letters + string.digits,
        "ascii_lowercase": string.ascii_lowercase,
        "ascii_uppercase": string.ascii_uppercase,
        "digits": string.digits,
        "ascii_letters": string.ascii_letters,
    }
    return charsets.get(name, name)


def _random_string(
    length: int, charset: str, rng: random.Random, exclude: str = ""
) -> str:
    available = [c for c in charset if c not in exclude]
    if not available:
        available = list(charset)
    return "".join(rng.choice(available) for _ in range(length))


def _generate_matching_string(
    pred: StringPredicate, axes: StringRulesAxes, rng: random.Random
) -> str:
    """Generate a string that matches the given predicate."""
    charset = _get_charset(axes.charset)
    lo, hi = axes.string_length_range

    match pred:
        case StringPredicateStartsWith(prefix=prefix):
            remaining_len = rng.randint(0, max(0, hi - len(prefix)))
            suffix = _random_string(remaining_len, charset, rng)
            return prefix + suffix

        case StringPredicateEndsWith(suffix=suffix):
            remaining_len = rng.randint(0, max(0, hi - len(suffix)))
            prefix = _random_string(remaining_len, charset, rng)
            return prefix + suffix

        case StringPredicateContains(substring=sub):
            before_len = rng.randint(0, (hi - len(sub)) // 2)
            after_len = rng.randint(0, (hi - len(sub)) // 2)
            before = _random_string(before_len, charset, rng)
            after = _random_string(after_len, charset, rng)
            return before + sub + after

        case StringPredicateIsAlpha():
            length = rng.randint(max(1, lo), hi)
            return _random_string(length, string.ascii_letters, rng)

        case StringPredicateIsDigit():
            length = rng.randint(max(1, lo), hi)
            return _random_string(length, string.digits, rng)

        case StringPredicateIsUpper():
            length = rng.randint(max(1, lo), hi)
            return _random_string(
                length, string.ascii_uppercase + string.digits, rng
            )

        case StringPredicateIsLower():
            length = rng.randint(max(1, lo), hi)
            return _random_string(
                length, string.ascii_lowercase + string.digits, rng
            )

        case StringPredicateLengthCmp(op=op, value=v):
            match op:
                case "lt":
                    length = rng.randint(max(1, lo), max(1, v - 1))
                case "le":
                    length = rng.randint(max(1, lo), max(1, v))
                case "gt":
                    length = rng.randint(v + 1, max(v + 1, hi))
                case "ge":
                    length = rng.randint(max(v, 1), max(v, hi))
                case "eq":
                    length = max(1, v)
                case _:
                    length = rng.randint(lo, hi)
            return _random_string(length, charset, rng)

        case _:
            return _random_string(rng.randint(lo, hi), charset, rng)


def _generate_non_matching_string(
    pred: StringPredicate, axes: StringRulesAxes, rng: random.Random
) -> str:
    """Generate a string that doesn't match the given predicate."""
    charset = _get_charset(axes.charset)
    lo, hi = axes.string_length_range

    match pred:
        case StringPredicateStartsWith(prefix=prefix):
            # Start with something different
            first_char = rng.choice([c for c in charset if c != prefix[0]])
            length = rng.randint(max(1, lo), hi)
            return first_char + _random_string(length - 1, charset, rng)

        case StringPredicateEndsWith(suffix=suffix):
            # End with something different
            last_char = rng.choice([c for c in charset if c != suffix[-1]])
            length = rng.randint(max(1, lo), hi)
            return _random_string(length - 1, charset, rng) + last_char

        case StringPredicateContains(substring=sub):
            # Generate without the substring
            length = rng.randint(max(1, lo), hi)
            result = _random_string(length, charset, rng)
            # Keep regenerating if we accidentally included it
            attempts = 0
            while sub in result and attempts < 10:
                result = _random_string(length, charset, rng)
                attempts += 1
            return result

        case StringPredicateIsAlpha():
            # Include a digit
            length = rng.randint(max(2, lo), hi)
            base = _random_string(length - 1, string.ascii_letters, rng)
            pos = rng.randint(0, len(base))
            return base[:pos] + rng.choice(string.digits) + base[pos:]

        case StringPredicateIsDigit():
            # Include a letter
            length = rng.randint(max(2, lo), hi)
            base = _random_string(length - 1, string.digits, rng)
            pos = rng.randint(0, len(base))
            return base[:pos] + rng.choice(string.ascii_letters) + base[pos:]

        case StringPredicateIsUpper():
            # Include lowercase
            length = rng.randint(max(2, lo), hi)
            base = _random_string(length - 1, string.ascii_uppercase, rng)
            pos = rng.randint(0, len(base))
            return base[:pos] + rng.choice(string.ascii_lowercase) + base[pos:]

        case StringPredicateIsLower():
            # Include uppercase
            length = rng.randint(max(2, lo), hi)
            base = _random_string(length - 1, string.ascii_lowercase, rng)
            pos = rng.randint(0, len(base))
            return base[:pos] + rng.choice(string.ascii_uppercase) + base[pos:]

        case StringPredicateLengthCmp(op=op, value=v):
            match op:
                case "lt":
                    length = rng.randint(max(v, 1), max(v, hi))
                case "le":
                    length = rng.randint(v + 1, max(v + 1, hi))
                case "gt":
                    length = rng.randint(max(1, lo), max(1, v))
                case "ge":
                    length = rng.randint(max(1, lo), max(1, v - 1))
                case "eq":
                    # Any length except v
                    length = v + 1 if v < hi else max(1, v - 1)
                case _:
                    length = rng.randint(lo, hi)
            return _random_string(length, charset, rng)

        case _:
            return _random_string(rng.randint(lo, hi), charset, rng)


def _generate_coverage_queries(
    spec: StringRulesSpec, axes: StringRulesAxes, rng: random.Random
) -> list[Query]:
    """Generate one input per rule that triggers that specific rule."""
    queries: list[Query] = []

    for i, rule in enumerate(spec.rules):
        # Generate a string that matches rule i but not rules 0..i-1
        attempts = 0
        while attempts < 20:
            s = _generate_matching_string(rule.predicate, axes, rng)
            # Check it doesn't match earlier rules
            matches_earlier = False
            for earlier_rule in spec.rules[:i]:
                if eval_string_predicate(earlier_rule.predicate, s):
                    matches_earlier = True
                    break
            if not matches_earlier:
                queries.append(
                    Query(
                        input=s,
                        output=eval_stringrules(spec, s),
                        tag=QueryTag.COVERAGE,
                    )
                )
                break
            attempts += 1
        else:
            # Fallback: just use a matching string
            s = _generate_matching_string(rule.predicate, axes, rng)
            queries.append(
                Query(
                    input=s,
                    output=eval_stringrules(spec, s),
                    tag=QueryTag.COVERAGE,
                )
            )

    return queries


def _generate_boundary_queries(
    spec: StringRulesSpec, axes: StringRulesAxes, rng: random.Random
) -> list[Query]:
    """Generate inputs that test rule precedence (match multiple rules)."""
    queries: list[Query] = []

    # Generate strings that could match multiple rules
    for i, rule in enumerate(spec.rules):
        # For pattern predicates, test exact matches and near-matches
        match rule.predicate:
            case StringPredicateStartsWith(prefix=prefix):
                # Exact prefix
                queries.append(
                    Query(
                        input=prefix,
                        output=eval_stringrules(spec, prefix),
                        tag=QueryTag.BOUNDARY,
                    )
                )
                # Prefix + extra char
                s = prefix + "x"
                queries.append(
                    Query(
                        input=s,
                        output=eval_stringrules(spec, s),
                        tag=QueryTag.BOUNDARY,
                    )
                )

            case StringPredicateEndsWith(suffix=suffix):
                # Exact suffix
                queries.append(
                    Query(
                        input=suffix,
                        output=eval_stringrules(spec, suffix),
                        tag=QueryTag.BOUNDARY,
                    )
                )

            case StringPredicateContains(substring=sub):
                # Just the substring
                queries.append(
                    Query(
                        input=sub,
                        output=eval_stringrules(spec, sub),
                        tag=QueryTag.BOUNDARY,
                    )
                )

            case StringPredicateLengthCmp(op=op, value=v):
                # Test boundary values
                if op in ("lt", "le"):
                    s = "x" * v
                    queries.append(
                        Query(
                            input=s,
                            output=eval_stringrules(spec, s),
                            tag=QueryTag.BOUNDARY,
                        )
                    )
                if op in ("gt", "ge") and v > 0:
                    s = "x" * v
                    queries.append(
                        Query(
                            input=s,
                            output=eval_stringrules(spec, s),
                            tag=QueryTag.BOUNDARY,
                        )
                    )

            case _:
                pass

    return queries


def _generate_typical_queries(
    spec: StringRulesSpec, axes: StringRulesAxes, rng: random.Random
) -> list[Query]:
    """Generate random typical strings."""
    queries: list[Query] = []
    charset = _get_charset(axes.charset)
    lo, hi = axes.string_length_range

    for _ in range(4):
        length = rng.randint(lo, hi)
        s = _random_string(length, charset, rng)
        queries.append(
            Query(
                input=s,
                output=eval_stringrules(spec, s),
                tag=QueryTag.TYPICAL,
            )
        )

    return queries


def _generate_adversarial_queries(
    spec: StringRulesSpec, axes: StringRulesAxes, rng: random.Random
) -> list[Query]:
    """Generate edge cases and strings that hit the default."""
    queries: list[Query] = []

    # Empty string
    queries.append(
        Query(
            input="",
            output=eval_stringrules(spec, ""),
            tag=QueryTag.ADVERSARIAL,
        )
    )

    # Single character
    queries.append(
        Query(
            input="x",
            output=eval_stringrules(spec, "x"),
            tag=QueryTag.ADVERSARIAL,
        )
    )

    # Try to hit the default (no rule matches)
    attempts = 0
    while attempts < 20:
        s = _random_string(rng.randint(3, 10), _get_charset(axes.charset), rng)
        matches_any = False
        for rule in spec.rules:
            if eval_string_predicate(rule.predicate, s):
                matches_any = True
                break
        if not matches_any:
            queries.append(
                Query(
                    input=s,
                    output=eval_stringrules(spec, s),
                    tag=QueryTag.ADVERSARIAL,
                )
            )
            break
        attempts += 1

    # Special strings
    special = [
        " ",
        "\t",
        "  spaces  ",
        "ALLCAPS",
        "alllower",
        "12345",
        "MixedCase123",
    ]
    for s in special:
        queries.append(
            Query(
                input=s,
                output=eval_stringrules(spec, s),
                tag=QueryTag.ADVERSARIAL,
            )
        )

    return queries


def generate_stringrules_queries(
    spec: StringRulesSpec,
    axes: StringRulesAxes,
    rng: random.Random | None = None,
) -> list[Query]:
    if rng is None:
        rng = random.Random()

    queries = [
        *_generate_coverage_queries(spec, axes, rng),
        *_generate_boundary_queries(spec, axes, rng),
        *_generate_typical_queries(spec, axes, rng),
        *_generate_adversarial_queries(spec, axes, rng),
    ]
    return _dedupe_queries(queries)


def _dedupe_queries(queries: list[Query]) -> list[Query]:
    seen: set[str] = set()
    result: list[Query] = []
    for q in queries:
        key = q.input
        if key not in seen:
            seen.add(key)
            result.append(q)
    return result
