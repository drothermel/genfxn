# Medium Fixes

Each touches 2-5 files with a clear strategy. Some involve a small design
choice noted inline. Expect 30-90 min each.

---

## ~~MF-1: CLI should reject mixing `--difficulty` with manual axes options~~ FIXED

**File:** `src/genfxn/cli.py`

Added a dict of all manual axes option names → values. After difficulty
validation, checks if any are non-None and errors with a message listing
the conflicting flags. Placed right after the `variant` check, before the
axes-building branch (~line 366).

---

## ~~MF-2: Warn when holdout matches zero tasks~~ FIXED

**File:** `src/genfxn/cli.py` (split command)

After `split_tasks()` returns, checks `len(result.test) == 0`. If so, prints
a warning to stderr with the holdout axis name and the first task's value at
that path (via `get_spec_value`) to help diagnose typos. Added
`get_spec_value` import from `core.codegen`.

---

## ~~MF-3: Composed predicate query generation should signal failure~~ FIXED

**Files:**
- `src/genfxn/stateful/queries.py`
- `src/genfxn/stringrules/queries.py`

Changed `_make_matching_value` / `_make_non_matching_value` (stateful) and
`_generate_matching_string` / `_generate_non_matching_string` (stringrules)
to return `None` when the brute-force fallback can't find a valid value.
Callers now skip queries when they get `None` instead of adding misleadingly-tagged
boundary/adversarial queries with values that don't satisfy the predicate.

---

## ~~MF-4: Require non-None description in Task model~~ FIXED

**Files:**
- `src/genfxn/core/models.py`
- `tests/test_splits.py`, `tests/test_core_validate.py`
- `scripts/patch_empty_descriptions.py` (removed — dead code)

Made `description` a required `str` field. Updated test helpers to include
`description="test task"`. Removed the now-unnecessary patch script.

---

## ~~MF-5: Export scoring constants from `difficulty.py` for `analyze_difficulty.py`~~ FIXED

**Files:**
- `src/genfxn/core/difficulty.py`
- `scripts/analyze_difficulty.py`

Extracted weight dicts as module-level constants in `difficulty.py`. Updated
`analyze_difficulty.py` to import them instead of duplicating the values.
Display-only axis labels kept in the script.

---

## ~~MF-6: Shared query deduplication utility~~ FIXED

**Files:**
- `src/genfxn/core/models.py`
- All four family `queries.py` files

Added `dedupe_queries()` to `core/models.py` with unified list→tuple hashability
handling. Replaced all four family-specific `_dedupe_queries` implementations
with imports from `core.models`.
