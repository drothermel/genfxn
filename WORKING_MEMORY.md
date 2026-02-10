# Working Memory

## Mission
Make `genfxn` a resilient research primitive: deterministic where expected,
strict in validation, and consistent across Python/Java/Rust runtime behavior.

## Keep Front-of-Mind
- Cross-language runtime parity is the core quality bar.
- Type strictness matters: avoid Python truthiness/coercion drift (`bool` vs
  `int`/`float`) in models, evaluators, split matching, and dedupe keys.
- Split behavior must be explicit and fail-closed on malformed/non-finite
  holdout inputs.
- Default verification mode (`standard`) skips `@pytest.mark.full`; parity and
  exhaustive checks require `--verification-level=full`.
- Safe execution paths must be lifecycle-safe (`close()`/process cleanup) and
  timeout-robust.

## Current State (2026-02-10)
- Latest review sweep items are closed, including:
  - nested type-sensitive holdout matching
  - exact/contains parser hardening (malformed JSON-like/scalar rejection,
    including case-mismatched JSON scalars)
  - bool-as-int rejection for remaining int-range axes and graph_queries
    direct-use contracts
  - NaN/frozenset dedupe + codegen NaN assertion correctness
  - split warning sentinel correctness (`None` preserved as first sample)
  - FSM `machine_type` deprecation signaling (kept, not removed)
- Tooling scope tightened:
  - Ruff includes Python files only
  - `ty` default scope is `src/` + `scripts/`

## Baseline Validation Snapshot
- `uv run pytest tests/ -q --verification-level=standard`
  - 1922 passed, 101 skipped
- `uv run ruff check .`
  - passed
- `uv run ty check`
  - passed

## Active Risks / Watchlist
- Parity reliability depends on Java/Rust toolchain availability in execution
  environment; ensure full-mode parity runs remain part of merge gating.
- When changing split/parser behavior, always keep library and CLI semantics
  aligned and covered by end-to-end CLI tests.
- Preserve strict type semantics recursively (nested containers), not only at
  top-level comparisons.

## Open Questions
- FSM `machine_type` remains behaviorally inert by design for now.
  - Current policy: deprecated and documented, intentionally retained for
    compatibility.

## Latest Intake (2026-02-10, strict surfacing + type strictness)
- `dedupe_queries` output equality still permits scalar/type conflation on
  duplicate inputs (`False` vs `0`, `1` vs `1.0`, and bool/int dict-key drift)
  because output comparison falls back to Python `==`.
- `StringRulesAxes` int-range fields still accept bool bounds via coercion
  (for example `False -> 0`, `True -> 1`), unlike other families that now
  reject bool bounds explicitly.
- `find_satisfying(...)` currently swallows all generator/predicate exceptions,
  which can hide real bugs in query synthesis paths and silently degrade
  coverage quality.

## Completed This Chunk (2026-02-10, strict surfacing + type strictness)
- Hardened output equality in `src/genfxn/core/models.py`:
  - `_query_outputs_equal(...)` is now explicitly type-sensitive (`type(...)`)
    before scalar fallback.
  - dict/set/frozenset output comparisons now use canonical structural freeze,
    closing bool/int and int/float conflation in nested/keyed outputs.
- Hardened `StringRulesAxes` input validation in
  `src/genfxn/stringrules/models.py`:
  - added pre-validation bool-bound rejection for
    `string_length_range`, `prefix_suffix_length_range`,
    `substring_length_range`, and `length_threshold_range`.
- Switched `find_satisfying(...)` in `src/genfxn/core/query_utils.py` to strict
  surfacing by removing broad exception swallowing; generator/predicate
  exceptions now propagate.
- Added/updated regressions:
  - `tests/test_core_models.py`
    - type-distinct output conflict cases (`False` vs `0`, `1` vs `1.0`,
      bool/int dict-key drift) for both dedupe paths.
  - `tests/test_stringrules.py`
    - bool bound rejection matrix for all int-range axes.
  - `tests/test_query_utils.py`
    - propagation assertions for generator/predicate `ValueError` and
      `RuntimeError`.
- Validation evidence:
  - `uv run pytest tests/test_core_models.py tests/test_query_utils.py`
    `tests/test_stringrules.py tests/test_stateful.py -q`
    `--verification-level=standard` -> 165 passed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` -> passed.

## Operating Workflow (for next tasks)
- Intake: capture only new facts, risks, and assumptions.
- Before edits: express concrete checklist items in `CURRENT_PLAN.md`.
- After each completed step: record outcome + minimal validation evidence.
- Prefer concise state over long historical logs; archive only when needed.
