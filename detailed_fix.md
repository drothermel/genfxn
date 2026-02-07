# Detailed Fixes

Architectural changes touching many files or requiring design decisions.
Each section includes context, trade-offs, and a proposed implementation plan.

---

## DF-1: Overhaul composed predicate difficulty scoring

**Files:**
- `src/genfxn/core/difficulty.py:135-148` (numeric `_predicate_score`)
- `src/genfxn/core/difficulty.py:320-334` (string `_string_predicate_score`)
- `tests/test_difficulty.py` (update expected values)
- `tests/test_presets.py` (thresholds may shift)

**Problem:** Numeric composed predicates all score 5 regardless of complexity:

```python
# difficulty.py:146-147
elif kind in ("not", "and", "or"):
    return 5
```

This means `not(even)` (trivially invertible) scores the same as
`and(mod_eq, gt, in_set)` (genuinely complex). Meanwhile, string predicates
already differentiate (`:330-334`):

```python
elif kind == "not":
    return 4
elif kind in ("and", "or"):
    operands = pred.get("operands", [])
    return 5 if len(operands) >= 3 else 4
```

**Impact:** Difficulty scores are inflated for simple composed predicates. This
affects preset accuracy — D3 tasks with `not(even)` score higher than they
should, potentially being misclassified as D4.

**Fix — align numeric scoring with string scoring:**

```python
# In _predicate_score:
elif kind == "not":
    return 4
elif kind in ("and", "or"):
    operands = pred.get("operands", [])
    return 5 if len(operands) >= 3 else 4
```

**Cascade effects:**
1. Some existing presets may need threshold adjustments. Currently D5 stateful
   relies on composed predicates scoring 5 to reach `raw >= 4.5`. With `not`
   scoring 4 instead of 5, the formula becomes:
   `0.4*4 + 0.3*4 + 0.3*5 = 1.6 + 1.2 + 1.5 = 4.3 → round → 4` (not 5!)
   So D5 presets that use `not` predicates would need to use `and`/`or` with 3+
   operands instead.

2. Run `uv run pytest tests/test_difficulty.py tests/test_presets.py -v` after the
   change. Expect failures in preset accuracy tests — update the presets in
   `core/presets.py` to only use 3-operand AND/OR for D5 where needed.

3. The `EDGE_DIFFICULTIES` set in `test_presets.py` may need updating.

**Implementation order:**
1. Change `_predicate_score` in `difficulty.py`
2. Run difficulty tests, fix expected values
3. Run preset tests, identify which presets now under-score
4. Update those presets in `core/presets.py` to use more complex predicates
5. Re-run all tests

---

## DF-2: Decide fate of the trace system — wire through or remove

**Files involved:**
- `src/genfxn/core/trace.py` (TraceStep, GenerationTrace models)
- `src/genfxn/core/models.py:28-30` (Task.trace field)
- `src/genfxn/piecewise/sampler.py` (~15 trace append calls)
- `src/genfxn/stateful/sampler.py` (~15 trace append calls)
- `src/genfxn/simple_algorithms/sampler.py` (trace appends)
- `src/genfxn/stringrules/sampler.py` (trace appends)
- `src/genfxn/*/task.py` (each family's task generation)
- `src/genfxn/suites/generate.py` (suite generation)
- `src/genfxn/cli.py` (CLI generate command)

**Current state:** `GenerationTrace` and `TraceStep` are fully modeled. The
samplers contain trace-appending code guarded by `if trace is not None`. But
no caller ever passes a trace list — `task.py` files create tasks with
`trace=None`, and the CLI/suites never request traces.

**Option A: Remove entirely (recommended if traces aren't needed soon)**

1. Delete `src/genfxn/core/trace.py`
2. Remove `trace` field from `Task` model in `core/models.py`
3. Remove `trace` parameter from all sampler functions
4. Remove all `if trace is not None: trace.append(...)` blocks
5. Remove `GenerationTrace` import from `core/models.py`
6. Update tests that reference `task.trace`

This removes ~100 lines of dead code across the codebase.

**Option B: Wire through fully (recommended if traces are valuable for debugging)**

1. Create a trace helper to reduce boilerplate. Add to `core/trace.py`:
   ```python
   def trace_step(
       trace: list[TraceStep] | None,
       step: str,
       choice: str,
       value: Any,
   ) -> None:
       if trace is not None:
           trace.append(TraceStep(step=step, choice=choice, value=value))
   ```

2. Replace all inline `if trace is not None: trace.append(TraceStep(...))` with
   `trace_step(trace, ...)` calls across all samplers.

3. In each family's `task.py`, create the trace and pass it through:
   ```python
   trace = GenerationTrace(family="stateful", steps=[])
   spec = sample_stateful_spec(axes, rng, trace=trace.steps)
   # ... later:
   task = Task(..., trace=trace)
   ```

4. In `suites/generate.py`, decide whether to include traces in suite output.
   Traces add bulk to JSONL files. Consider a `--include-traces` flag in the CLI.

5. In `cli.py`, add `--trace` flag that enables trace collection.

**Recommendation:** If traces are mainly useful during development/debugging,
Option A is cleaner. Traces can always be re-added later with the helper pattern.
The current half-implemented state is the worst of both worlds.

---

## DF-3: Shared predicate matching utilities in core

**Files:**
- New: `src/genfxn/core/query_utils.py`
- `src/genfxn/stateful/queries.py:41-118`
- `src/genfxn/stringrules/queries.py:20-234`
- `src/genfxn/piecewise/queries.py` (simpler version of same pattern)

**Problem:** Stateful and stringrules query generators both implement nearly
identical brute-force matching logic for composed predicates. The pattern is:

```python
# Try N times to find a value satisfying some condition
for _ in range(N):
    v = random_value(...)
    if condition(v):
        return v
return random_value(...)  # silent fallback
```

This appears 4 times (matching + non-matching x stateful + stringrules),
and the fallback behavior is the core of bug MF-3.

**Fix — create `core/query_utils.py`:**

```python
"""Shared query generation utilities."""
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def find_satisfying(
    generate: Callable[[], T],
    predicate: Callable[[T], bool],
    max_attempts: int = 100,
) -> tuple[T, bool]:
    """Try to find a value satisfying predicate.

    Returns (value, success). If success is False, value is a random
    fallback that may not satisfy the predicate.
    """
    for _ in range(max_attempts):
        v = generate()
        if predicate(v):
            return v, True
    return generate(), False
```

**Usage in stateful/queries.py:**

```python
from genfxn.core.query_utils import find_satisfying

# In _make_matching_value, composed predicate branch:
case PredicateNot() | PredicateAnd() | PredicateOr():
    val, ok = find_satisfying(
        generate=lambda: rng.randint(lo, hi),
        predicate=lambda v: eval_predicate(pred, v),
    )
    return val  # caller can check `ok` if we change signature
```

**Usage in stringrules/queries.py:**

```python
case StringPredicateNot() | StringPredicateAnd() | StringPredicateOr():
    val, ok = find_satisfying(
        generate=lambda: _random_string(rng.randint(lo, hi), charset, rng),
        predicate=lambda s: eval_string_predicate(pred, s),
        max_attempts=50,
    )
    return val
```

**Also move `dedupe_queries` here** (see MF-6) to make `core/query_utils.py`
the single home for shared query logic.

**Implementation order:**
1. Create `core/query_utils.py` with `find_satisfying` and `dedupe_queries`
2. Refactor stateful/queries.py to use it
3. Refactor stringrules/queries.py to use it
4. Run tests: `uv run pytest tests/ -v`

---

## DF-4: Testing improvements

**Files:**
- `tests/test_core_dsl.py` (hash uniqueness)
- `tests/test_presets.py` (fix flakiness)
- New: `tests/test_query_quality.py` (query failure modes)

### DF-4a: Corpus-level hash uniqueness test

**Problem:** Only 2-3 specs are tested for ID uniqueness. With 64-bit hashes
the collision risk is low, but a birthday-paradox-style test builds confidence.

**Add to `tests/test_core_dsl.py`:**
```python
def test_id_uniqueness_across_families():
    """Generate many specs and verify all task_ids are unique."""
    from genfxn.core.codegen import task_id_from_spec
    rng = random.Random(42)
    ids = set()
    for family in ["piecewise", "stateful", "simple_algorithms", "stringrules"]:
        for _ in range(200):
            # Generate random spec via each family's sampler
            spec = sample_random_spec(family, rng)  # need a helper
            tid = task_id_from_spec(family, spec.model_dump())
            assert tid not in ids, f"Collision: {tid}"
            ids.add(tid)
    assert len(ids) == 800
```

This requires a helper that samples a random spec per family. Each family's
`task.py` already has generation functions that can be called with default axes.

### DF-4b: Fix preset test flakiness

**Problem:** `test_presets.py` uses `random.Random(42)` but the 70%/50% pass
thresholds make tests non-deterministic relative to changes in sampler code.
A sampler change that doesn't affect correctness could break these tests.

**Fix options:**
1. **Pin seeds AND expected counts** — make tests fully deterministic
2. **Increase sample count** from 50 to 200 and tighten thresholds to 85%
3. **Accept a range** — e.g., "at least 35/50 must hit target difficulty"

Option 1 is most robust but means any sampler change requires updating expected
counts. Option 3 is most pragmatic. Current approach is option 3 with loose
thresholds — just tighten them slightly and add a comment explaining the rationale.

### DF-4c: Test query generation failure modes

**Add `tests/test_query_quality.py`:**

```python
"""Tests that query generation handles hard-to-match predicates gracefully."""

def test_stateful_composed_predicate_boundary_queries():
    """Verify boundary queries actually test predicate boundaries."""
    # Create a spec with AND(mod_eq(97,0), gt(50)) — very restrictive
    # with value_range=(-10, 10), no value satisfies this
    # Verify: either no boundary query is generated, or the query
    # output matches spec eval (not a garbage value labeled as boundary)

def test_stringrules_contains_long_substring():
    """Verify Contains predicate doesn't crash when substring > string_length."""
    # After QF-4 is applied, this should work without ValueError

def test_coverage_queries_cover_all_rules():
    """Verify coverage queries actually exercise each stringrule."""
    # Generate a spec with 3 non-overlapping rules
    # Verify coverage queries include one input per rule
    # Verify each coverage query triggers its intended rule, not an earlier one
```

---

## DF-5: Suite generation observability

**Files:**
- `src/genfxn/suites/generate.py`
- `src/genfxn/cli.py` (optional: expose metadata in CLI)

**Problem:** Several issues compound:
1. Pool generation silently discards specs that don't hit target difficulty
   (`generate.py:542-543`). No visibility into hit rate.
2. Pool size doubles per retry (`generate.py:687`), potentially generating
   12000+ candidates to find 50. No logging of efficiency.
3. Generated tasks don't include the axes used for sampling, making it hard
   to analyze "which configurations produce D5 reliably."

**Fix approach:**

### 5a. Add generation statistics

Add a return type for pool generation stats:

```python
class PoolStats(BaseModel):
    total_sampled: int
    duplicates: int
    wrong_difficulty: int
    errors: int
    candidates: int

    @computed_field
    @property
    def hit_rate(self) -> float:
        return self.candidates / max(1, self.total_sampled)
```

Update `generate_pool` to track and return these alongside candidates:

```python
def generate_pool(...) -> tuple[list[Candidate], PoolStats]:
    stats = PoolStats(...)
    # ... existing loop, incrementing stats counters ...
    return candidates, stats
```

### 5b. Log stats in `generate_suite`

```python
for attempt in range(max_retries + 1):
    current_pool_size = pool_size * (2**attempt)
    candidates, stats = generate_pool(...)
    logger.info(
        f"{family} D{difficulty} attempt {attempt}: "
        f"sampled={stats.total_sampled}, hit_rate={stats.hit_rate:.1%}, "
        f"candidates={stats.candidates}"
    )
```

Use Python's `logging` module so it's configurable. In the CLI, set log level
via `--verbose` flag.

### 5c. Populate `Task.axes` field

The `Task` model already has `axes: dict[str, Any] | None`. In each family's
`task.py`, the axes are available. Just pass them through:

```python
task = Task(
    ...,
    axes=axes.model_dump(),
)
```

Currently the `suites/generate.py` flow has axes available at pool generation
time. Thread them into the candidate tuple and then into the final Task.

This enables downstream analysis like:
```python
# "What axes configurations produce D5 stateful tasks?"
d5_tasks = [t for t in tasks if t.difficulty == 5]
axes_configs = [t.axes for t in d5_tasks]
```

---

## DF-6: Stringrules overlap control doesn't track composed predicate operands

**Files:**
- `src/genfxn/stringrules/sampler.py:230-260`

**Problem:** The overlap control logic tracks `used_pred_types` to avoid
duplicate predicates across rules. But for composed predicates (NOT, AND, OR),
only the outer type is tracked — not the operands inside.

Example: Two rules could both use `NOT(IS_ALPHA)` without triggering overlap
detection, because only `NOT` is added to `used_pred_types`.

**Current code (`sampler.py:243`):**
```python
used_pred_types.add(pred_type)
```

**Fix approach:**

For composed predicates, also track the operand types:

```python
used_pred_types.add(pred_type)
# Also track operands for overlap detection
if hasattr(pred, 'operand'):
    operand_kind = pred.operand.kind if hasattr(pred.operand, 'kind') else None
    if operand_kind:
        used_pred_types.add(operand_kind)
elif hasattr(pred, 'operands'):
    for op in pred.operands:
        op_kind = op.kind if hasattr(op, 'kind') else None
        if op_kind:
            used_pred_types.add(op_kind)
```

**Alternatively**, track at the string level using the serialized predicate dict.
This is more robust but changes the semantics of `used_pred_types` from
"types used" to "configurations used":

```python
import srsly
pred_key = srsly.json_dumps(pred.model_dump(), sort_keys=True)
used_pred_configs.add(pred_key)
```

**Trade-off:** The first approach prevents reuse of operand types across rules
(e.g., if rule 1 uses NOT(IS_ALPHA), rule 2 can't use IS_ALPHA at all). This
may be too aggressive. The second approach prevents exact duplicates but allows
different compositions of the same operand types.

**Recommendation:** Use the first approach for `OverlapLevel.NONE` and the
second for `OverlapLevel.LOW`. For `OverlapLevel.HIGH`, no change needed (overlap
is allowed).
