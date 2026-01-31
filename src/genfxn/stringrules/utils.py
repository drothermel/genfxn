"""Stringrules helpers for charset resolution and random string generation."""

import random
import string


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
    """Return a random string from charset (length), excluding chars in exclude.

    Raises ValueError if length > 0 and charset after exclude is empty.
    """
    available = [c for c in charset if c not in exclude]
    if not available:
        available = list(charset)
    if length > 0 and not available:
        raise ValueError(
            "charset (after exclude) must contain at least one character"
        )
    return "".join(rng.choice(available) for _ in range(length))
