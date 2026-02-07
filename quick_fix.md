# Quick Fixes

Isolated, low-risk changes. Each is a few lines in a single file.
No design decisions needed — the correct fix is obvious.

---

## ~~QF-1: CLI help text says `--n-rules (1-8)`, should be `(1-10)`~~ FIXED

**File:** `src/genfxn/cli.py:278`

Changed help text from `1-8` to `1-10`.

---

## ~~QF-2: `_matches_holdout` missing catch-all → implicit None return~~ FIXED

**File:** `src/genfxn/splits.py`

Added `case _: raise ValueError(...)` to the match statement.

---

## ~~QF-3: `HoldoutType.RANGE` on string-valued fields → TypeError~~ FIXED

**File:** `src/genfxn/splits.py`

Added `isinstance(value, (int, float))` type guard in the RANGE branch.
Returns `False` for non-numeric values instead of crashing.

---

## ~~QF-4: StringPredicateContains matching can crash on long substrings~~ FIXED

**File:** `src/genfxn/stringrules/queries.py:43-48`

Replaced `(hi - len(sub)) // 2` with `max(0, hi - len(sub)) // 2` to prevent
negative values being passed to `rng.randint`.

---

## QF-5: Repeated `atom_types` list defined 3 times in stateful sampler

**File:** `src/genfxn/stateful/sampler.py:65-113`

**Problem:** The identical 7-element `atom_types` list is copy-pasted into the NOT,
AND, and OR branches of `sample_predicate`.

**Fix:** Define once at module level (after the imports, before `sample_predicate`):
```python
_ATOM_PREDICATE_TYPES = [
    PredicateType.EVEN,
    PredicateType.ODD,
    PredicateType.LT,
    PredicateType.LE,
    PredicateType.GT,
    PredicateType.GE,
    PredicateType.MOD_EQ,
]
```

Then replace all three inline lists with `_ATOM_PREDICATE_TYPES`.
Same list is used in `stringrules/sampler.py` for string predicates — apply
the same pattern there with `_ATOM_STRING_PREDICATE_TYPES`.

---

## QF-6: `PredicateType` enum reads from `model_fields` (fragile)

**File:** `src/genfxn/core/predicates.py:98-109`

**Problem:** Enum values are derived via `PredicateEven.model_fields["kind"].default`.
If a Literal type annotation ever changes, the enum silently drifts.
Compare with `core/string_predicates.py:96-107` which uses direct string literals — more robust.

**Current:**
```python
class PredicateType(str, Enum):
    EVEN = PredicateEven.model_fields["kind"].default
    ODD = PredicateOdd.model_fields["kind"].default
    ...
```

**Fix:** Use direct string values (matching the pattern in `string_predicates.py`):
```python
class PredicateType(str, Enum):
    EVEN = "even"
    ODD = "odd"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    MOD_EQ = "mod_eq"
    IN_SET = "in_set"
    NOT = "not"
    AND = "and"
    OR = "or"
```

---

## QF-7: `_parse_range` error message doesn't show expected format

**File:** `src/genfxn/cli.py` — the `_parse_range` function

**Problem:** When range parsing fails, the error says "Invalid range" but doesn't
show the expected format. Users may try `5-10` instead of `5,10`.

**Fix:** Update the BadParameter message to include an example:
```python
raise typer.BadParameter(f"Invalid range '{value}': expected 'LO,HI' (e.g., '5,10')")
```
