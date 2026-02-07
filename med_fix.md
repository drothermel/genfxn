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

## MF-3: Composed predicate query generation should signal failure

**Files:**
- `src/genfxn/stateful/queries.py:71-76` and `:111-116`
- `src/genfxn/stringrules/queries.py:117-122` and `:226-231`

**Problem:** Both `_make_matching_value` and `_make_non_matching_value` in
stateful/queries.py, plus `_generate_matching_string` and
`_generate_non_matching_string` in stringrules/queries.py, have a brute-force
fallback for composed predicates (NOT/AND/OR). After 50-100 attempts they
return a random value that may not satisfy the predicate.

This silently degrades query quality — boundary queries may not actually test
predicate boundaries.

**Fix approach — return a success flag:**

For stateful (`stateful/queries.py`), change the return to a tuple:

```python
# In _make_matching_value, at the composed predicate branch:
case PredicateNot() | PredicateAnd() | PredicateOr():
    for _ in range(100):
        v = rng.randint(lo, hi)
        if eval_predicate(pred, v):
            return v
    # Fallback: return value anyway but log warning
    import warnings
    warnings.warn(
        f"Could not find matching value for {pred} in ({lo}, {hi}) after 100 attempts",
        stacklevel=2,
    )
    return rng.randint(lo, hi)
```

Same pattern for `_make_non_matching_value` and the stringrules equivalents.

**Why warnings over exceptions:** These are best-effort query generators.
A warning lets the pipeline complete while making failures visible in logs.
The validation step will catch any query whose output doesn't match the spec,
so the data quality is ultimately protected.

**Alternative (more robust):** Have the caller check whether the returned value
actually matches, and skip adding the query if it doesn't:
```python
match_val = _make_matching_value(pred, (lo, hi), rng)
if eval_predicate(pred, match_val):
    # add the boundary query
else:
    pass  # skip this query, don't silently add a bad one
```

This approach is cleaner because it doesn't add misleadingly-tagged queries.
Apply this pattern at:
- `stateful/queries.py:165-166` (boundary query generation)
- `stringrules/queries.py:247` (coverage query generation)

**Testing:** Add a test with a deliberately hard-to-satisfy composed predicate
(e.g., `AND(mod_eq(97, 0), gt(1000))` with value_range `(-10, 10)`) and
verify the query generator doesn't produce bogus boundary queries.

---

## MF-4: Require non-None description in Task model

**Files:**
- `src/genfxn/core/models.py:40-42`
- `scripts/patch_empty_descriptions.py` (can be removed after)
- Each family's `task.py` (verify they already set description — they do)

**Problem:** `description: str | None = None` allows tasks to be created without
descriptions. `scripts/patch_empty_descriptions.py` exists solely to fix this
after the fact.

**Fix:**

In `core/models.py`, change:
```python
description: str | None = Field(
    default=None, description="Natural language description of the task"
)
```
to:
```python
description: str = Field(description="Natural language description of the task")
```

**Impact check:** Before making this change, verify that all task creation paths
provide descriptions. Search for `Task(` across the codebase:
- Each family's `task.py` already calls `describe_task()` and passes it
- `suites/generate.py` constructs tasks with descriptions
- Tests that construct Task objects directly will need updating

After confirming all paths provide descriptions, the patch script is dead code
and can be removed.

**Testing:** Verify existing tests still pass (some test helpers may construct
Task objects without description — those need fixing).

---

## MF-5: Export scoring constants from `difficulty.py` for `analyze_difficulty.py`

**Files:**
- `src/genfxn/core/difficulty.py`
- `scripts/analyze_difficulty.py:60-125`

**Problem:** `analyze_difficulty.py` manually re-defines the weight tables and
axis-score mappings from `difficulty.py`. The script itself notes:
`# NOTE: Keep these in sync with the actual difficulty calculation logic.`

**Fix approach:**

1. In `difficulty.py`, expose the weights as module-level constants:
   ```python
   PIECEWISE_WEIGHTS = {"branches": 0.4, "expr_type": 0.4, "coeff": 0.2}
   STATEFUL_WEIGHTS = {"template": 0.4, "predicate": 0.3, "transform": 0.3}
   SIMPLE_ALGORITHMS_WEIGHTS = {"template": 0.5, "mode": 0.3, "edge": 0.2}
   STRINGRULES_WEIGHTS = {"rules": 0.4, "predicate": 0.3, "transform": 0.3}
   ```
   These are already implicit in the `_*_difficulty` functions. Just extract them
   as named constants and reference them from the functions.

2. In `analyze_difficulty.py`, import and use them:
   ```python
   from genfxn.core.difficulty import (
       PIECEWISE_WEIGHTS, STATEFUL_WEIGHTS,
       SIMPLE_ALGORITHMS_WEIGHTS, STRINGRULES_WEIGHTS,
   )
   ```
   Remove the duplicated definitions (lines 65-125).

**Note:** The axis-score mappings in the script are more descriptive (human labels
like `"EVEN/ODD"`) and won't map 1:1 to the scoring functions. You may want to
keep those as display labels in the script while importing the numeric weights.

---

## MF-6: Shared query deduplication utility

**Files:**
- `src/genfxn/core/models.py` (or a new `core/queries.py`)
- `src/genfxn/piecewise/queries.py`
- `src/genfxn/stateful/queries.py`
- `src/genfxn/simple_algorithms/queries.py`
- `src/genfxn/stringrules/queries.py`

**Problem:** Each family implements its own `_dedupe_queries()` with slightly
different key extraction:
- Piecewise: `q.input` (int)
- Stateful: `tuple(q.input)` (list → tuple)
- Simple algorithms: `tuple(q.input)` (list → tuple)
- Stringrules: `q.input` (str)

All are doing the same thing: dedupe by input value, keeping first occurrence.

**Fix:** Add to `core/models.py` (or create `core/queries.py`):
```python
def dedupe_queries(queries: list[Query]) -> list[Query]:
    """Deduplicate queries by input, keeping first occurrence."""
    seen: set[Any] = set()
    result: list[Query] = []
    for q in queries:
        key = tuple(q.input) if isinstance(q.input, list) else q.input
        if key not in seen:
            seen.add(key)
            result.append(q)
    return result
```

Then replace each family's `_dedupe_queries` with an import. This also
centralizes the hashability logic (list → tuple conversion).
