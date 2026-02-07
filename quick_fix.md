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

## ~~QF-5: Repeated `atom_types` list defined 3 times in stateful sampler~~ FIXED

**File:** `src/genfxn/stateful/sampler.py`, `src/genfxn/stringrules/sampler.py`

Extracted `_ATOM_PREDICATE_TYPES` and `_COMPOSED_PREDICATE_TYPES` as module-level
constants in both files, replacing 3 inline copies each.

---

## ~~QF-6: `PredicateType` enum reads from `model_fields` (fragile)~~ FIXED

**File:** `src/genfxn/core/predicates.py`

Changed enum values from `model_fields["kind"].default` to direct string literals,
matching the pattern already used in `string_predicates.py`.

---

## ~~QF-7: `_parse_range` error message doesn't show expected format~~ FIXED

**File:** `src/genfxn/cli.py`

Updated all three `_parse_range` error messages to include the expected format
and an example: `"Invalid range '...': expected 'LO,HI' (e.g., '5,10')"`.
