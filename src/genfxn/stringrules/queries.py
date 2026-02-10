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
from genfxn.core.string_transforms import (
    StringTransform,
    StringTransformPipeline,
    StringTransformReplace,
)
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import StringRulesAxes, StringRulesSpec
from genfxn.stringrules.utils import _get_charset, _random_string


class StringRulesQueryGenerationError(RuntimeError):
    """Raised when required replace-aware coverage cannot be generated."""


def _first_matching_rule_index(spec: StringRulesSpec, s: str) -> int | None:
    for i, rule in enumerate(spec.rules):
        if eval_string_predicate(rule.predicate, s):
            return i
    return None


def _iter_replace_old_values(transform: StringTransform) -> list[str]:
    olds: list[str] = []
    if isinstance(transform, StringTransformReplace):
        return [transform.old]
    if isinstance(transform, StringTransformPipeline):
        for step in transform.steps:
            olds.extend(_iter_replace_old_values(step))
    return olds


def _random_string_with_old(
    old: str,
    charset: str,
    lo: int,
    hi: int,
    rng: random.Random,
) -> str | None:
    if len(old) > hi:
        return None
    min_len = max(lo, len(old))
    if min_len > hi:
        return None

    length = rng.randint(min_len, hi)
    extra = length - len(old)
    before_len = rng.randint(0, extra)
    after_len = extra - before_len
    before = _random_string(before_len, charset, rng)
    after = _random_string(after_len, charset, rng)
    return before + old + after


def _length_cmp_allows_old(
    op: str, value: int, old_len: int, lo: int, hi: int
) -> bool:
    match op:
        case "lt":
            lower = max(lo, old_len)
            upper = min(hi, value - 1)
            return lower <= upper
        case "le":
            lower = max(lo, old_len)
            upper = min(hi, value)
            return lower <= upper
        case "gt":
            lower = max(lo, old_len, value + 1)
            return lower <= hi
        case "ge":
            lower = max(lo, old_len, value)
            return lower <= hi
        case "eq":
            if value < lo or value > hi:
                return False
            return old_len <= value
        case _:
            return old_len <= hi


def _is_old_proven_unreachable_for_predicate(
    pred: StringPredicate,
    old: str,
    axes: StringRulesAxes,
) -> bool:
    lo, hi = axes.string_length_range

    if len(old) > hi:
        return True

    match pred:
        case StringPredicateStartsWith(prefix=prefix):
            return max(len(prefix), len(old)) > hi
        case StringPredicateEndsWith(suffix=suffix):
            return max(len(suffix), len(old)) > hi
        case StringPredicateContains():
            return len(old) > hi
        case StringPredicateIsAlpha():
            return not old.isalpha()
        case StringPredicateIsDigit():
            return not old.isdigit()
        case StringPredicateIsUpper():
            return any(ch.islower() for ch in old)
        case StringPredicateIsLower():
            return any(ch.isupper() for ch in old)
        case StringPredicateLengthCmp(op=op, value=v):
            return not _length_cmp_allows_old(op, v, len(old), lo, hi)
        case StringPredicateAnd(operands=ops):
            return any(
                _is_old_proven_unreachable_for_predicate(op, old, axes)
                for op in ops
            )
        case StringPredicateOr(operands=ops):
            return all(
                _is_old_proven_unreachable_for_predicate(op, old, axes)
                for op in ops
            )
        case StringPredicateNot():
            # We intentionally avoid over-asserting impossibility for NOT.
            return False
        case _:
            return False


def _choose_length_for_predicate_with_old(
    pred: StringPredicate,
    old_len: int,
    axes: StringRulesAxes,
    rng: random.Random,
) -> int | None:
    lo, hi = axes.string_length_range

    match pred:
        case StringPredicateLengthCmp(op=op, value=v):
            match op:
                case "lt":
                    lower = max(lo, old_len)
                    upper = min(hi, v - 1)
                case "le":
                    lower = max(lo, old_len)
                    upper = min(hi, v)
                case "gt":
                    lower = max(lo, old_len, v + 1)
                    upper = hi
                case "ge":
                    lower = max(lo, old_len, v)
                    upper = hi
                case "eq":
                    if v < lo or v > hi or old_len > v:
                        return None
                    lower = v
                    upper = v
                case _:
                    lower = max(lo, old_len)
                    upper = hi
        case _:
            lower = max(lo, old_len)
            upper = hi

    if lower > upper:
        return None
    return rng.randint(lower, upper)


def _generate_matching_string_with_old(
    pred: StringPredicate,
    old: str,
    axes: StringRulesAxes,
    rng: random.Random,
) -> str | None:
    if _is_old_proven_unreachable_for_predicate(pred, old, axes):
        return None

    charset = _get_charset(axes.charset)
    alpha_charset = "".join(ch for ch in charset if ch.isalpha())
    digit_charset = "".join(ch for ch in charset if ch.isdigit())
    upper_charset = "".join(ch for ch in charset if ch.isupper())
    lower_charset = "".join(ch for ch in charset if ch.islower())
    upper_tail_charset = "".join(ch for ch in charset if not ch.islower())
    lower_tail_charset = "".join(ch for ch in charset if not ch.isupper())
    lo, hi = axes.string_length_range

    def _valid(candidate: str) -> str | None:
        if not (lo <= len(candidate) <= hi):
            return None
        if old not in candidate:
            return None
        if eval_string_predicate(pred, candidate):
            return candidate
        return None

    match pred:
        case StringPredicateStartsWith(prefix=prefix):
            if old in prefix:
                length = _choose_length_for_predicate_with_old(
                    pred, len(prefix), axes, rng
                )
                if length is None or length < len(prefix):
                    return None
                suffix = _random_string(length - len(prefix), charset, rng)
                return _valid(prefix + suffix)

            base_len = len(prefix) + len(old)
            length = _choose_length_for_predicate_with_old(
                pred, base_len, axes, rng
            )
            if length is None:
                return None
            extra = length - base_len
            before_len = rng.randint(0, extra)
            after_len = extra - before_len
            before = _random_string(before_len, charset, rng)
            after = _random_string(after_len, charset, rng)
            return _valid(prefix + before + old + after)

        case StringPredicateEndsWith(suffix=suffix):
            if old in suffix:
                length = _choose_length_for_predicate_with_old(
                    pred, len(suffix), axes, rng
                )
                if length is None or length < len(suffix):
                    return None
                prefix = _random_string(length - len(suffix), charset, rng)
                return _valid(prefix + suffix)

            base_len = len(old) + len(suffix)
            length = _choose_length_for_predicate_with_old(
                pred, base_len, axes, rng
            )
            if length is None:
                return None
            extra = length - base_len
            before_len = rng.randint(0, extra)
            middle_len = extra - before_len
            before = _random_string(before_len, charset, rng)
            middle = _random_string(middle_len, charset, rng)
            return _valid(before + old + middle + suffix)

        case StringPredicateContains():
            candidate = _random_string_with_old(old, charset, lo, hi, rng)
            if candidate is None:
                return None
            return _valid(candidate)

        case StringPredicateIsAlpha():
            if not alpha_charset or not old.isalpha():
                return None
            length = _choose_length_for_predicate_with_old(
                pred, len(old), axes, rng
            )
            if length is None:
                return None
            extra = length - len(old)
            before_len = rng.randint(0, extra)
            after_len = extra - before_len
            before = _random_string(before_len, alpha_charset, rng)
            after = _random_string(after_len, alpha_charset, rng)
            return _valid(before + old + after)

        case StringPredicateIsDigit():
            if not digit_charset or not old.isdigit():
                return None
            length = _choose_length_for_predicate_with_old(
                pred, len(old), axes, rng
            )
            if length is None:
                return None
            extra = length - len(old)
            before_len = rng.randint(0, extra)
            after_len = extra - before_len
            before = _random_string(before_len, digit_charset, rng)
            after = _random_string(after_len, digit_charset, rng)
            return _valid(before + old + after)

        case StringPredicateIsUpper():
            if not upper_tail_charset or any(ch.islower() for ch in old):
                return None

            length = _choose_length_for_predicate_with_old(
                pred, len(old), axes, rng
            )
            if length is None:
                return None

            extra = length - len(old)
            old_has_upper = any(ch.isupper() for ch in old)
            if not old_has_upper and extra == 0:
                if length + 1 > hi:
                    return None
                extra = 1
                length += 1
            if not old_has_upper and not upper_charset:
                return None

            before_len = rng.randint(0, extra)
            after_len = extra - before_len
            before = _random_string(before_len, upper_tail_charset, rng)
            after = _random_string(after_len, upper_tail_charset, rng)
            candidate = before + old + after

            if not old_has_upper:
                index = rng.randint(0, len(candidate))
                marker = rng.choice(upper_charset)
                candidate = candidate[:index] + marker + candidate[index:]
                if len(candidate) > hi:
                    return None

            return _valid(candidate)

        case StringPredicateIsLower():
            if not lower_tail_charset or any(ch.isupper() for ch in old):
                return None

            length = _choose_length_for_predicate_with_old(
                pred, len(old), axes, rng
            )
            if length is None:
                return None

            extra = length - len(old)
            old_has_lower = any(ch.islower() for ch in old)
            if not old_has_lower and extra == 0:
                if length + 1 > hi:
                    return None
                extra = 1
                length += 1
            if not old_has_lower and not lower_charset:
                return None

            before_len = rng.randint(0, extra)
            after_len = extra - before_len
            before = _random_string(before_len, lower_tail_charset, rng)
            after = _random_string(after_len, lower_tail_charset, rng)
            candidate = before + old + after

            if not old_has_lower:
                index = rng.randint(0, len(candidate))
                marker = rng.choice(lower_charset)
                candidate = candidate[:index] + marker + candidate[index:]
                if len(candidate) > hi:
                    return None

            return _valid(candidate)

        case StringPredicateLengthCmp():
            length = _choose_length_for_predicate_with_old(
                pred, len(old), axes, rng
            )
            if length is None:
                return None
            extra = length - len(old)
            before_len = rng.randint(0, extra)
            after_len = extra - before_len
            before = _random_string(before_len, charset, rng)
            after = _random_string(after_len, charset, rng)
            return _valid(before + old + after)

        case StringPredicateNot() | StringPredicateAnd() | StringPredicateOr():
            for _ in range(20):
                candidate = _random_string_with_old(old, charset, lo, hi, rng)
                if candidate is None:
                    return None
                valid = _valid(candidate)
                if valid is not None:
                    return valid
            return None

        case _:
            return None


def _find_first_match_candidate(
    spec: StringRulesSpec,
    axes: StringRulesAxes,
    rng: random.Random,
    *,
    rule_index: int,
    required_old: str | None = None,
    attempts: int = 80,
) -> str | None:
    rule = spec.rules[rule_index]
    charset = _get_charset(axes.charset)
    lo, hi = axes.string_length_range

    for _ in range(attempts):
        if required_old is None:
            candidate = _generate_matching_string(rule.predicate, axes, rng)
            if candidate is None:
                candidate = _random_string(rng.randint(lo, hi), charset, rng)
        else:
            candidate = _generate_matching_string_with_old(
                rule.predicate, required_old, axes, rng
            )
            if candidate is None:
                candidate = _random_string_with_old(
                    required_old, charset, lo, hi, rng
                )

        if candidate is None:
            continue
        if required_old is not None and required_old not in candidate:
            continue
        if _first_matching_rule_index(spec, candidate) == rule_index:
            return candidate

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
    """Generate coverage inputs, including replace-aware witnesses."""
    queries: list[Query] = []
    failures: list[str] = []

    for i, rule in enumerate(spec.rules):
        base = _find_first_match_candidate(
            spec,
            axes,
            rng,
            rule_index=i,
            attempts=80,
        )
        if base is not None:
            queries.append(
                Query(
                    input=base,
                    output=eval_stringrules(spec, base),
                    tag=QueryTag.COVERAGE,
                )
            )

        replace_olds = _iter_replace_old_values(rule.transform)
        if not replace_olds:
            continue

        if base is None:
            base = _find_first_match_candidate(
                spec,
                axes,
                rng,
                rule_index=i,
                attempts=240,
            )
        if base is None:
            # Rule appears unreachable as first-match; skip replace obligations.
            continue

        for old in replace_olds:
            if old == "":
                continue
            if _is_old_proven_unreachable_for_predicate(
                rule.predicate, old, axes
            ):
                continue

            witness = _find_first_match_candidate(
                spec,
                axes,
                rng,
                rule_index=i,
                required_old=old,
                attempts=140,
            )
            if witness is None:
                witness = _find_first_match_candidate(
                    spec,
                    axes,
                    rng,
                    rule_index=i,
                    required_old=old,
                    attempts=240,
                )
            if witness is None:
                failures.append(f"rule={i} old={old!r}")
                continue

            queries.append(
                Query(
                    input=witness,
                    output=eval_stringrules(spec, witness),
                    tag=QueryTag.COVERAGE,
                )
            )

    if failures:
        rendered = ", ".join(failures)
        raise StringRulesQueryGenerationError(
            "unable to generate replace-aware coverage for "
            f"{len(failures)} obligations: {rendered}"
        )

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
