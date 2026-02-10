import random

from genfxn.core.models import Query, QueryTag, dedupe_queries
from genfxn.core.query_utils import find_satisfying
from genfxn.core.string_predicates import (
    StringPredicate,
    StringPredicateAnd,
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
    eval_string_predicate,
)
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import StringRulesAxes, StringRulesSpec
from genfxn.stringrules.utils import _get_charset, _random_string


def _first_matching_rule_index(spec: StringRulesSpec, s: str) -> int | None:
    for i, rule in enumerate(spec.rules):
        if eval_string_predicate(rule.predicate, s):
            return i
    return None


def _generate_matching_string(
    pred: StringPredicate, axes: StringRulesAxes, rng: random.Random
) -> str | None:
    """Generate a string that matches the given predicate."""
    charset = _get_charset(axes.charset)
    alpha_charset = "".join(ch for ch in charset if ch.isalpha())
    digit_charset = "".join(ch for ch in charset if ch.isdigit())
    upper_charset = "".join(ch for ch in charset if ch.isupper())
    lower_charset = "".join(ch for ch in charset if ch.islower())
    upper_tail_charset = "".join(ch for ch in charset if not ch.islower())
    lower_tail_charset = "".join(ch for ch in charset if not ch.isupper())
    lo, hi = axes.string_length_range

    def _sample_length(
        min_len: int = 0, max_len: int | None = None
    ) -> int | None:
        upper = hi if max_len is None else min(max_len, hi)
        lower = max(lo, min_len)
        if lower > upper:
            return None
        return rng.randint(lower, upper)

    def _valid(s: str) -> str | None:
        if lo <= len(s) <= hi and eval_string_predicate(pred, s):
            return s
        return None

    match pred:
        case StringPredicateStartsWith(prefix=prefix):
            length = _sample_length(min_len=len(prefix))
            if length is None:
                return None
            suffix = _random_string(length - len(prefix), charset, rng)
            return _valid(prefix + suffix)

        case StringPredicateEndsWith(suffix=suffix):
            length = _sample_length(min_len=len(suffix))
            if length is None:
                return None
            prefix = _random_string(length - len(suffix), charset, rng)
            return _valid(prefix + suffix)

        case StringPredicateContains(substring=sub):
            length = _sample_length(min_len=len(sub))
            if length is None:
                return None
            slack = length - len(sub)
            before_len = rng.randint(0, slack)
            after_len = slack - before_len
            before = _random_string(before_len, charset, rng)
            after = _random_string(after_len, charset, rng)
            return _valid(before + sub + after)

        case StringPredicateIsAlpha():
            length = _sample_length(min_len=1)
            if length is None or not alpha_charset:
                return None
            return _valid(_random_string(length, alpha_charset, rng))

        case StringPredicateIsDigit():
            length = _sample_length(min_len=1)
            if length is None or not digit_charset:
                return None
            return _valid(_random_string(length, digit_charset, rng))

        case StringPredicateIsUpper():
            length = _sample_length(min_len=1)
            if length is None or not upper_charset or not upper_tail_charset:
                return None
            tail = _random_string(
                max(0, length - 1),
                upper_tail_charset,
                rng,
            )
            return _valid(rng.choice(upper_charset) + tail)

        case StringPredicateIsLower():
            length = _sample_length(min_len=1)
            if length is None or not lower_charset or not lower_tail_charset:
                return None
            tail = _random_string(
                max(0, length - 1),
                lower_tail_charset,
                rng,
            )
            return _valid(rng.choice(lower_charset) + tail)

        case StringPredicateLengthCmp(op=op, value=v):
            match op:
                case "lt":
                    length = _sample_length(max_len=v - 1)
                case "le":
                    length = _sample_length(max_len=v)
                case "gt":
                    length = _sample_length(min_len=v + 1)
                case "ge":
                    length = _sample_length(min_len=v)
                case "eq":
                    length = _sample_length(min_len=v, max_len=v)
                case _:
                    length = _sample_length()
            if length is None:
                return None
            return _valid(_random_string(length, charset, rng))

        case StringPredicateNot() | StringPredicateAnd() | StringPredicateOr():
            return find_satisfying(
                lambda: _random_string(rng.randint(lo, hi), charset, rng),
                lambda s: eval_string_predicate(pred, s),
                max_attempts=50,
            )

        case _:
            return _valid(_random_string(rng.randint(lo, hi), charset, rng))


def _generate_non_matching_string(
    pred: StringPredicate, axes: StringRulesAxes, rng: random.Random
) -> str | None:
    """Generate a string that doesn't match the given predicate."""
    charset = _get_charset(axes.charset)
    alpha_charset = "".join(ch for ch in charset if ch.isalpha())
    digit_charset = "".join(ch for ch in charset if ch.isdigit())
    upper_charset = "".join(ch for ch in charset if ch.isupper())
    lower_charset = "".join(ch for ch in charset if ch.islower())
    lo, hi = axes.string_length_range

    def _sample_length(min_len: int = 0) -> int | None:
        lower = max(lo, min_len)
        if lower > hi:
            return None
        return rng.randint(lower, hi)

    match pred:
        case StringPredicateStartsWith(prefix=prefix):
            # Start with something different
            if not prefix:
                return None
            excluded = [c for c in charset if c != prefix[0]]
            if not excluded:
                return None
            first_char = rng.choice(excluded)
            length = _sample_length(min_len=1)
            if length is None:
                return None
            return first_char + _random_string(length - 1, charset, rng)

        case StringPredicateEndsWith(suffix=suffix):
            # End with something different
            if not suffix:
                return None
            excluded = [c for c in charset if c != suffix[-1]]
            if not excluded:
                return None
            last_char = rng.choice(excluded)
            length = _sample_length(min_len=1)
            if length is None:
                return None
            return _random_string(length - 1, charset, rng) + last_char

        case StringPredicateContains(substring=sub):
            # Generate without the substring
            length = _sample_length(min_len=1)
            if length is None:
                return None
            result = _random_string(length, charset, rng)
            # Keep regenerating if we accidentally included it
            attempts = 0
            while sub in result and attempts < 10:
                result = _random_string(length, charset, rng)
                attempts += 1
            if sub in result:
                return None
            return result

        case StringPredicateIsAlpha():
            # Include a non-alpha character from the configured charset.
            length = _sample_length(min_len=1)
            breakers = [ch for ch in charset if not ch.isalpha()]
            if length is None or not breakers:
                return None
            if length == 1:
                return rng.choice(breakers)
            if not alpha_charset:
                return _random_string(length, "".join(breakers), rng)
            base = _random_string(length - 1, alpha_charset, rng)
            pos = rng.randint(0, len(base))
            return base[:pos] + rng.choice(breakers) + base[pos:]

        case StringPredicateIsDigit():
            # Include a non-digit character from the configured charset.
            length = _sample_length(min_len=1)
            breakers = [ch for ch in charset if not ch.isdigit()]
            if length is None or not breakers:
                return None
            if length == 1:
                return rng.choice(breakers)
            if not digit_charset:
                return _random_string(length, "".join(breakers), rng)
            base = _random_string(length - 1, digit_charset, rng)
            pos = rng.randint(0, len(base))
            return base[:pos] + rng.choice(breakers) + base[pos:]

        case StringPredicateIsUpper():
            # Force not-isupper() via lowercase character, or no cased chars.
            length = _sample_length(min_len=1)
            lower_breakers = [ch for ch in charset if ch.islower()]
            non_cased = [ch for ch in charset if not ch.isalpha()]
            if length is None:
                return None
            if length == 1:
                if lower_breakers:
                    return rng.choice(lower_breakers)
                if non_cased:
                    return rng.choice(non_cased)
                return None
            if lower_breakers and upper_charset:
                base = _random_string(length - 1, upper_charset, rng)
                pos = rng.randint(0, len(base))
                return base[:pos] + rng.choice(lower_breakers) + base[pos:]
            if lower_breakers:
                return _random_string(length, "".join(lower_breakers), rng)
            if non_cased:
                return _random_string(length, "".join(non_cased), rng)
            return None

        case StringPredicateIsLower():
            # Force not-islower() via uppercase character, or no cased chars.
            length = _sample_length(min_len=1)
            upper_breakers = [ch for ch in charset if ch.isupper()]
            non_cased = [ch for ch in charset if not ch.isalpha()]
            if length is None:
                return None
            if length == 1:
                if upper_breakers:
                    return rng.choice(upper_breakers)
                if non_cased:
                    return rng.choice(non_cased)
                return None
            if upper_breakers and lower_charset:
                base = _random_string(length - 1, lower_charset, rng)
                pos = rng.randint(0, len(base))
                return base[:pos] + rng.choice(upper_breakers) + base[pos:]
            if upper_breakers:
                return _random_string(length, "".join(upper_breakers), rng)
            if non_cased:
                return _random_string(length, "".join(non_cased), rng)
            return None

        case StringPredicateLengthCmp(op=op, value=v):
            match op:
                case "lt":
                    lower = max(lo, v)
                    if lower > hi:
                        return None
                    length = rng.randint(lower, hi)
                case "le":
                    lower = max(lo, v + 1)
                    if lower > hi:
                        return None
                    length = rng.randint(lower, hi)
                case "gt":
                    # Non-matching: length <= v; clamp upper to hi
                    upper = min(v, hi)
                    if upper < lo:
                        return None
                    length = rng.randint(lo, upper)
                case "ge":
                    # Non-matching: length < v; clamp upper to hi
                    upper = min(v - 1, hi)
                    if upper < lo:
                        return None
                    length = rng.randint(lo, upper)
                case "eq":
                    # Any length except v
                    candidates = [
                        candidate
                        for candidate in range(lo, hi + 1)
                        if candidate != v
                    ]
                    if not candidates:
                        return None
                    length = rng.choice(candidates)
                case _:
                    length = rng.randint(lo, hi)
            return _random_string(length, charset, rng)

        case StringPredicateNot() | StringPredicateAnd() | StringPredicateOr():
            return find_satisfying(
                lambda: _random_string(rng.randint(lo, hi), charset, rng),
                lambda s: not eval_string_predicate(pred, s),
                max_attempts=50,
            )

        case _:
            return _random_string(rng.randint(lo, hi), charset, rng)


def _generate_coverage_queries(
    spec: StringRulesSpec, axes: StringRulesAxes, rng: random.Random
) -> list[Query]:
    """Generate one input per rule that triggers that specific rule."""
    queries: list[Query] = []

    for i, rule in enumerate(spec.rules):
        # Generate a string that first-matches exactly rule i.
        attempts = 0
        while attempts < 20:
            s = _generate_matching_string(rule.predicate, axes, rng)
            if s is None:
                break
            if _first_matching_rule_index(spec, s) == i:
                queries.append(
                    Query(
                        input=s,
                        output=eval_stringrules(spec, s),
                        tag=QueryTag.COVERAGE,
                    )
                )
                break
            attempts += 1
        # Fallback: skip if we could not find a first-match sample for rule i.
        # Do not mislabel shadowed samples as COVERAGE.

    return queries


def _generate_boundary_queries(
    spec: StringRulesSpec, _axes: StringRulesAxes, _rng: random.Random
) -> list[Query]:
    """Generate inputs that test rule precedence (match multiple rules)."""
    queries: list[Query] = []

    lo, hi = _axes.string_length_range
    charset = _get_charset(_axes.charset)
    charset_set = set(charset)
    boundary_char = charset[0] if charset else ""

    def _chars_ok(s: str) -> bool:
        return all(ch in charset_set for ch in s)

    def _append_if_in_range(s: str) -> None:
        if lo <= len(s) <= hi and _chars_ok(s):
            queries.append(
                Query(
                    input=s,
                    output=eval_stringrules(spec, s),
                    tag=QueryTag.BOUNDARY,
                )
            )

    # Generate strings that could match multiple rules
    for rule in spec.rules:
        # For pattern predicates, test exact matches and near-matches
        match rule.predicate:
            case StringPredicateStartsWith(prefix=prefix):
                _append_if_in_range(prefix)
                # Prefix + extra char
                s = prefix + boundary_char
                _append_if_in_range(s)

            case StringPredicateEndsWith(suffix=suffix):
                _append_if_in_range(suffix)

            case StringPredicateContains(substring=sub):
                _append_if_in_range(sub)

            case StringPredicateLengthCmp(op=op, value=v):
                # Test boundary values
                if op in ("lt", "le"):
                    s = boundary_char * v
                    _append_if_in_range(s)
                if op in ("gt", "ge") and v > 0:
                    s = boundary_char * v
                    _append_if_in_range(s)

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

    lo, hi = axes.string_length_range
    charset = _get_charset(axes.charset)
    charset_set = set(charset)

    def _chars_ok(s: str) -> bool:
        return all(ch in charset_set for ch in s)

    def _append_if_in_range(s: str) -> None:
        if lo <= len(s) <= hi and _chars_ok(s):
            queries.append(
                Query(
                    input=s,
                    output=eval_stringrules(spec, s),
                    tag=QueryTag.ADVERSARIAL,
                )
            )

    # Empty string
    _append_if_in_range("")

    # Single character
    if charset:
        _append_if_in_range(charset[0])

    # Try to hit the default (no rule matches)
    attempts = 0
    while attempts < 20:
        s = _random_string(rng.randint(lo, hi), charset, rng)
        matches_any = False
        for rule in spec.rules:
            if eval_string_predicate(rule.predicate, s):
                matches_any = True
                break
        if not matches_any:
            _append_if_in_range(s)
            break
        attempts += 1

    # Special strings
    special: list[str] = []
    if charset:
        c0 = charset[0]
        c1 = charset[1] if len(charset) > 1 else c0
        c2 = charset[2] if len(charset) > 2 else c1
        special = [
            c0 * 2,
            c1 * 5,
            c0 + c1 + c2,
            c2 + c1 + c0,
            (c0 + c1) * 3,
        ]
    for s in special:
        _append_if_in_range(s)

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
    return dedupe_queries(queries)
