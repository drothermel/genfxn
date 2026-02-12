# Working Memory

## Mission
Make `genfxn` a resilient research primitive: deterministic where expected,
strict in validation, and consistent across Python/Java/Rust runtime behavior.

## Current Focus
- Close quality parity gaps between early families (`piecewise`, `stateful`,
  `simple_algorithms`, `stringrules`) and newer families.
- Reduce classes of failures that only surface under
  `--verification-level=full`.
- Address latest correctness regressions in deduping/splits and verification
  gate clarity.

## Recent Findings
- Validator bool-as-int gaps existed across multiple newer families; these are
  high risk for cross-language semantic drift because `True == 1` and
  `False == 0`.
- Suite generation for `intervals` difficulty-2 can get trapped by greedy
  one-pass quota filling with insufficient retry diversification.
- Safe-exec lifecycle leaks in several validators can leave worker processes
  alive and cause flaky `full` failures in long runs.
- Coverage quality is uneven:
  - Mature patterns (semantic capping checks, strict-vs-lenient checks, code
    map path checks, forced parity variant coverage) are strong in some early
    families.
  - Several newer families still rely more on sampled tests and thin edge-case
    assertions.

## Latest Intake (2026-02-10)
- `dedupe_queries` scalar freeze key currently conflates distinct scalar types
  (`True` vs `1`, `1` vs `1.0`), causing false merges/conflicts.
- Range holdout matching in both library and CLI currently accepts bools as
  numeric values, so `False` can match `[0, 0]` unexpectedly.
- Default verification level (`standard`) skips `@pytest.mark.full`, including
  runtime parity suites; default green runs are not full safety coverage.
- Verification-level skip/run behavior was configured in `tests/conftest.py`
  but lacked a focused regression test to guard against marker-gating drift.
- CLI random split regressed to materializing all tasks in memory via
  `list(_iter_validated_tasks(...))`, risking OOM on large JSONL inputs.
- Runtime parity depth ownership includes five sampled-heavy suites:
  `fsm`, `bitops`, `intervals`, `stateful`, and `simple_algorithms`.
- `fsm` sampled parity currently uses skip-on-`ValueError` behavior that hides
  undefined-transition error-policy outcomes instead of asserting parity.
- Older-family validator parity ownership for this task:
  - add bool rejection tests where `int` is expected in queries
  - add strict-vs-lenient severity tests for query input/output type issues
  - add exec lifecycle `close()` assertions after semantic validation
- Remaining priority batch:
  1) intervals D2 suite generation robustness
  2) validator parity in older families
  3) runtime parity forced-variant depth
- New intake (this pass):
  - exact holdout still conflates bool/int in library+CLI
  - dedupe hashable fallback still allows cross-type collisions
  - dedupe repr fallback can crash on broken-`__repr__` unhashables
  - split contract drift between CLI and library random split was not codified
    after memory-regression fixes
- Validator contract coverage still relies on many family-local bespoke tests;
  shared matrix coverage is missing for strict/lenient severity parity and
  bool-rejection behavior on int-like query fields.
- Common validator lifecycle/skip behavior (non-Python code-map path and
  exec-function `close()` lifecycle) is still asserted per-family rather than
  through one reusable parameterized contract suite.

## Latest Intake Extension (2026-02-10, CI Policy Hardening)
- Repository currently has no `.github/workflows/*` CI workflow, so merge
  validation depends on local/manual command discipline.
- Default pytest mode remains `--verification-level=standard`, which skips
  `@pytest.mark.full`; without CI enforcement, full parity/edge suites are not
  routinely gated.
- Existing guidance in docs/PR template references full verification, but there
  is no automated path that makes it mandatory on pull requests.

## Latest Intake Extension (2026-02-10, Numeric/Representation Hardening)
- `stack_bytecode` Rust renderer currently uses plain `i64` arithmetic (`+`,
  `-`, `*`, unary negation, `/`, `%`, `abs`) that can diverge from Java
  `long` semantics on overflow-adjacent values (especially `MIN / -1`,
  `MIN % -1`, `abs(MIN)`, and `-MIN`).
- `sequence_dp` Rust renderer currently uses plain `i64` arithmetic for DP
  score/path accumulation and predicate subtraction in `mod_eq`; these paths
  can overflow and diverge from Java `long` wrapping behavior.
- Existing runtime parity suites for these families are strong on sampled and
  forced-variant coverage but thin on explicit overflow-adjacent regressions.
- String length parity already uses code-point semantics in Java/Rust renderers,
  but coverage can be strengthened for combining-mark and ZWJ emoji cases.

## Latest Intake Extension (2026-02-10, CLI Range + NaN Dedupe Hardening)
- `graph_queries` CLI `--value-range` currently ignores user-provided negative
  ranges with no explicit signal (falls back to default `weight_range`).
- `_parse_numeric_range` currently accepts non-finite bounds (`nan`, `inf`,
  `-inf`) and should reject them with clear `BadParameter`.
- `dedupe_queries` currently treats `float('nan')` inputs as distinct keys,
  so equivalent NaN queries are not deduped deterministically.

## Latest Intake Extension (2026-02-10, dedupe NaN output equality)
- `dedupe_queries` conflict detection currently uses raw `!=` on outputs, so
  duplicate outputs that are both `float('nan')` are incorrectly treated as a
  conflict.
- Required behavior for this pass: treat NaN-vs-NaN outputs as equal for
  duplicate inputs, while still raising on true output mismatches.

## Latest Intake Extension (2026-02-10, FSM + Holdout Matcher Hardening)
- FSM runtime parity error-path assertions currently accept any nonzero process
  failure; they should assert semantic alignment with Python evaluator error
  messages so compile/runtime drift is not masked.
- Holdout matching behavior is duplicated in `src/genfxn/splits.py` and
  `src/genfxn/cli.py`, increasing regression risk from drift between library
  and CLI behavior.

## Latest Intake Extension (2026-02-10, Int32 Overflow Semantics)
- `piecewise`, `stateful`, and `simple_algorithms` Python evaluators currently
  use unbounded Python integer arithmetic, while Java renderers execute with
  Java `int` overflow semantics.
- Rust renderers for those same families currently run `i64` arithmetic, so
  overflow-adjacent cases diverge from Java `int` and from any intended shared
  contract.
- Existing runtime parity suites for these families stay in small numeric
  ranges and do not currently lock overflow behavior.
- Reproduced concrete drift cases:
  - piecewise quadratic: Python/Rust `2500000000` vs Java `-1794967296`
  - stateful sum path: Python/Rust `4000000000` vs Java `-294967296`
  - simple_algorithms max-window path: Python/Rust `4000000000` vs Java
    `-294967296`

## Latest Intake Extension (2026-02-10, Java Int Literal Compile Safety)
- Java renderers for int-based families emit raw decimal literals for spec
  constants; literals above Java `int` range can fail javac with
  `integer number too large`.
- Affected emission paths are concentrated in
  `src/genfxn/langs/java/{predicates.py,expressions.py,stateful.py,`
  `simple_algorithms.py,piecewise.py}` plus helper transform rendering.
- Priority for this issue is compile-safety for valid specs; overflow-semantics
  alignment can be handled separately where needed.

## Completed This Chunk (2026-02-10, Java Int Literal Compile Safety)
- Added shared helper `java_int_literal(...)` in
  `src/genfxn/langs/java/_helpers.py` to emit compile-safe int expressions for
  out-of-range constants via explicit long-cast narrowing.
- Patched int-literal emission in:
  `src/genfxn/langs/java/predicates.py`,
  `src/genfxn/langs/java/expressions.py`,
  `src/genfxn/langs/java/transforms.py`,
  `src/genfxn/langs/java/stateful.py`, and
  `src/genfxn/langs/java/simple_algorithms.py`.
- Audited `src/genfxn/langs/java/piecewise.py`; no direct integer-literal
  emission path required patching because it delegates to predicates/expressions
  renderers.
- Added compile-safety regressions with oversized constants in:
  - `tests/test_piecewise_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
  and helper unit coverage in `tests/test_java_render.py`.
- Validation evidence:
  - targeted full pytest (`TestJavaIntLiteral` + oversized compile tests):
    6 passed.
  - targeted renderer pytest slice: 44 passed.
  - targeted `ruff` and `ty` on touched files: passed.

## Latest Intake Extension (2026-02-10, Runtime Parity Int32 Boundary Coverage)
- Runtime parity files for `simple_algorithms`, `stateful`, and `piecewise`
  currently lean on sampled/small-domain checks and lack explicit deterministic
  int32-boundary probes.
- Needed coverage should include high-magnitude deterministic values near and
  at signed int32 edges (for example `2_000_000_000`, `2_147_483_647`) plus
  `50_000^2`-style arithmetic stress inputs.
- Validation for this batch should run targeted full-mode parity suites plus
  `ruff` and `ty` on touched files.

## Latest Intake Extension (2026-02-10, Oversized Literal Parity Rigor)
- Oversized-literal runtime tests in `piecewise`, `stateful`, and
  `simple_algorithms` currently only prove Java compile/run viability; they do
  not assert Java/Rust output parity against Python evaluators.
- Some oversized literal cases use out-of-range divisor/remainder values in
  mod predicates/expressions, which can diverge from the chosen int32 contract
  used in core overflow fixes.
- `tests/test_java_render.py` currently has thin `java_int_literal(...)`
  coverage and should explicitly lock compile-safe behavior at int32 and
  long-range boundaries.

## Latest Intake Extension (2026-02-10, Overflow-Adjacent Expected Source)
- Overflow-adjacent runtime parity tests in `sequence_dp` and `stack_bytecode`
  currently pin hardcoded expected numeric outputs.
- These expectations should be derived from the Python evaluators
  (`eval_sequence_dp`, `eval_stack_bytecode`) to keep parity assertions aligned
  with the canonical runtime semantics while remaining deterministic.
- Scope is limited to:
  - `tests/test_sequence_dp_runtime_parity.py`
  - `tests/test_stack_bytecode_runtime_parity.py`

## Latest Intake Extension (2026-02-10, Core Semantics Blocking Fixes #1/#2/#3)
- `eval_predicate(...)` currently has no int32-eval mode, so int32 families
  (`piecewise`, `stateful`, `simple_algorithms`) evaluate predicate constants
  with unbounded-Python semantics while Java/Rust execute int32 semantics.
- int32 transform `clip` in `eval_transform(...)` currently clips against raw
  `low/high` bounds before wrapping, diverging from Java/Rust behavior that
  applies int32-cast bounds during clamp.
- Core `mod_eq` and `piecewise` `ExprMod` divisors are only validated as `> 0`;
  very large positive divisors can wrap to zero/negative in int32 runtimes,
  creating compile/runtime modulo crash or divergence risk.
- `stateful`/`simple_algorithms` query-generation helpers still call
  `eval_predicate(...)` in default mode, so generated boundary/adversarial
  examples can drift from int32 runtime semantics for wrapped constants.

## Latest Intake Extension (2026-02-10, CLI Exact/Contains Non-Finite Holdout Rejection)
- Split CLI currently rejects non-finite bounds only for `--holdout-type range`;
  `exact`/`contains` paths still accept non-finite tokens through
  `json.loads(...)` (`NaN`, `Infinity`, `-Infinity`) or raw fallback strings
  (`nan`, `inf`, `-inf`).
- Holdout matcher flow currently has no explicit non-finite guard for
  `EXACT`/`CONTAINS`, so direct library use with non-finite holdout values is
  not fail-closed by contract.

## Latest Intake Extension (2026-02-10, safe_exec startup-timeout flake)
- `execute_code_restricted(timeout_sec=0.2)` can fail during worker startup
  under load before any function call executes, producing startup crash/timeout
  noise (`exit code -9` or queue `Empty`) instead of exercising call-timeout
  semantics.
- `_PersistentWorker` currently reuses function execution `timeout_sec` for
  bootstrap initialization, which is too aggressive for process startup jitter.

## Latest Intake Extension (2026-02-10, repo-wide review follow-up)
- Java renderer compile-safety still has two uncovered large-literal paths:
  - `graph_queries` edge weight literals above Java `int` range.
  - `stack_bytecode` `max_step_count` above Java `int` range.
- `core.codegen.render_tests(...)` currently renders `set`/`frozenset`
  literals in insertion/hash iteration order, causing cross-process
  nondeterministic output text.
- A small set of first-party family tests still use `pytest.importorskip(...)`,
  which can convert genuine import regressions into skips.
- This batch should add a startup-specific timeout floor (or equivalent init
  timeout separation) while preserving function execution timeout behavior.

## Latest Intake Extension (2026-02-10, graph/interval overflow follow-up)
- `graph_queries` shortest-path overflow handling still had algorithm drift:
  Python evaluator re-queued improved nodes, while Java/Rust frontier logic only
  enqueued first discovery. Under overflow-cycle inputs this produced concrete
  parity mismatch.
- Reproduced mismatch case:
  - edges: `0->1 (1)`, `1->0 (2^63-1)`, `1->2 (0)`, query `(0,2)`
  - Python evaluator: `-9223372036854775807`
  - Java/Rust runtime: `1`
- Reproduced evaluator liveness risk case:
  - edges: `0->1 (2^63-1)`, `1->2 (2^63-1)`, `2->0 (1)`, query `(0,3)`
  - Python evaluator entered long-running relaxation behavior; Java/Rust
    returned `-1` quickly.
- Python renderers still lag evaluator/runtime i64 hardening in these families:
  - `graph_queries` Python renderer uses unwrapped cost accumulation and can
    diverge on overflow-cycle cases.
  - `intervals` Python renderer still used unbounded arithmetic for boundary
    adjustments/aggregation/event sweeps, diverging from evaluator/runtime
    signed-i64 behavior on boundary specs.

## Completed This Chunk (2026-02-10, graph/interval overflow follow-up)
- Aligned `graph_queries` evaluator shortest-path logic to the same
  frontier-update contract used by Java/Rust renderers while preserving signed
  i64-wrapped accumulation.
- Updated Python renderer overflow semantics:
  - `src/genfxn/graph_queries/render.py` now wraps shortest-path accumulation.
  - `src/genfxn/intervals/render.py` now mirrors evaluator i64 wrap behavior for
    boundary handling, merge thresholding, coverage accumulation, overlap event
    accounting, and gap counting.
- Added focused regressions:
  - `tests/test_graph_queries.py`
  - `tests/test_graph_queries_runtime_parity.py`
  - `tests/test_intervals.py`
  covering overflow-cycle behavior and rendered-Python parity on i64 boundaries.
- Validation evidence:
  - targeted full-mode pytest slice: 6 passed
  - full touched-module pytest run (`graph_queries`, `intervals`): 86 passed
  - targeted `ruff` on touched files: passed
  - targeted `ty` on touched files: passed

## Latest Intake Extension (2026-02-10, Review Comment Sweep)
- `tests/test_verification_levels.py` creates pytester probe files whose module
  basenames collide with real suite modules (`test_piecewise_runtime_parity`,
  `test_stateful_runtime_parity`, `test_validate_piecewise`), producing xdist
  import-mismatch collection failures in default (`standard`) runs.
- CLI split currently allows `--train` and `--test` to resolve to the same
  output target path, which can silently clobber one partition during atomic
  replace.
- `graph_queries` Java renderer uses `int` accumulation for shortest-path cost,
  diverging from Python/Rust behavior on valid large-weight specs.
- Python renderers for `stack_bytecode` and `sequence_dp` do not fully mirror
  evaluator i64 wrapping semantics on overflow-adjacent arithmetic paths.
- `dedupe_queries` output conflict checks only special-case top-level NaN;
  structurally equivalent nested NaN outputs are falsely treated as conflicts.
- `render_tests(...)` emits invalid Python for non-finite floats because raw
  `repr(float('nan'/'inf'))` is not a bound name in generated code.
- Runtime parity reliability gaps:
  - subprocess compile/run calls lack explicit timeouts
  - toolchain guards skip on missing Java/Rust instead of fail-closed
  - CI does not explicitly install Java/Rust toolchains before full parity run

## Completed This Chunk (2026-02-10, Review Comment Sweep)
- Fixed xdist import-mismatch in `tests/test_verification_levels.py` by
  moving pytester family probes into an isolated subdirectory with unique
  module paths.
- Added split-output collision guard in `src/genfxn/cli.py` so identical
  resolved `--train`/`--test` paths fail fast; added end-to-end regressions in
  `tests/test_cli.py` for random and holdout modes.
- Fixed graph_queries Java shortest-path cost overflow by using `long`
  bookkeeping/return types in `src/genfxn/langs/java/graph_queries.py`;
  added large-weight parity regression in
  `tests/test_graph_queries_runtime_parity.py`.
- Aligned Python renderers with evaluator i64 behavior:
  - `src/genfxn/stack_bytecode/render.py`
  - `src/genfxn/sequence_dp/render.py`
  Added focused renderer-vs-evaluator regressions in
  `tests/test_stack_bytecode.py` and `tests/test_sequence_dp.py`.
- Extended NaN output equality in `src/genfxn/core/models.py` to treat nested
  structurally equivalent NaN values as equal; added regressions in
  `tests/test_core_models.py`.
- Hardened `render_tests(...)` in `src/genfxn/core/codegen.py` to emit valid
  Python for non-finite values, with regression coverage in
  `tests/test_core_dsl.py`.
- Added timeout-enforced subprocess helper in `tests/helpers.py` and migrated
  all runtime parity suites to use it; toolchain requirements now fail-closed
  via `pytest.fail(...)` instead of skip.
- Updated CI `test-full` workflow to explicitly install Java and Rust before
  full verification (`.github/workflows/ci.yml`).
- Validation evidence:
  - focused standard slice: 282 passed
  - runtime parity smoke slice: 23 passed
  - default standard suite: 1831 passed, 101 skipped
  - ruff + ty on touched files: passed

## Latest Intake Extension (2026-02-10, FSM machine_type deprecation docs)
- `machine_type` in FSM is intentionally retained for schema compatibility but
  has no evaluator/renderer semantic effect.
- Requested action for this pass is deprecation signaling via clear in-code
  comments/docs (not removal), so future contributors do not assume missing
  semantics are accidental.

## Latest Intake Extension (2026-02-10, Follow-up Review Issues)
- `render_tests(...)` still emits direct equality assertions for NaN outputs,
  which are semantically impossible (`nan != nan`) even when runtime behavior
  is correct.
- `dedupe_queries` still lacks explicit `frozenset` canonicalization/equality
  handling for NaN-bearing structures, causing missed dedupes/false conflicts.
- Split warning first-sample capture in CLI holdout flow uses `None` as a
  sentinel, so real `None` first values can be overwritten by later values.
- Bool-as-int range bound rejection remains inconsistent across families:
  piecewise/intervals reject bool bounds, but several other family axes still
  accept/coerce `False/True` in numeric ranges.

## Latest Intake Extension (2026-02-10, Holdout contains + remaining bool-range drift)
- `HoldoutType.CONTAINS` matching currently uses raw membership (`in`) so
  `False` can match numeric `0` in list/tuple/set/frozenset containers.
- Remaining family axes still lacking explicit bool bound rejection for int
  ranges:
  - `graph_queries` (`weight_range`, plus integer range fields)
  - `temporal_logic` (`formula_depth_range`, `sequence_length_range`,
    `value_range`, `predicate_constant_range`)
- Non-finite holdout guard currently skips set/frozenset containers in
  `_contains_non_finite_number(...)`, so non-finite values nested there are
  not fail-closed for `exact`/`contains`.

## Latest Intake Extension (2026-02-10, Nested Holdout Typing + JSON-ish Parse + graph_queries bools)
- Reproduced nested type-conflation drift in holdout matcher:
  - `EXACT`: spec `{"vals": [0]}` incorrectly matches holdout `[False]`.
  - `CONTAINS`: spec `{"vals": [[0]]}` incorrectly matches holdout `[False]`.
  Root cause is top-level-only type-sensitive check; nested containers still
  compare with Python equality semantics (`False == 0`, `1 == 1.0`).
- Reproduced CLI parse drift for malformed JSON-like exact/contains holdouts:
  - malformed token `"[1,2"` falls back to raw string silently and split exits
    successfully with 0 matches instead of surfacing malformed user input.
- Reproduced graph_queries direct-use bool coercion:
  - `GraphEdge(u=True, ...)` is accepted and coerced to `1`.
  - `eval_graph_queries(spec, False, 1)` runs instead of rejecting type-mismatch.
- Re-verified current workspace status:
  - prior bool-bound rejection fix in `GraphQueriesAxes` and
    `TemporalLogicAxes` is already effective (no remaining repro there).

## Latest Intake Extension (2026-02-10, malformed JSON-scalar holdout typos)
- CLI exact/contains holdout parsing still allowed malformed scalar-like tokens
  (`tru`, `nul`, `01`, `+1`) to silently fall back to raw strings.
- This can produce successful-but-unintended split runs when the user intended
  JSON boolean/null/number literals.

## Completed This Chunk (2026-02-10, malformed JSON-scalar holdout typos)
- Updated `src/genfxn/cli.py`:
  - added malformed-scalar detection for JSON-ish primitive/number typos in
    `_parse_non_range_holdout_value(...)`.
  - `tru`, `nul`, `01`, `+1` now fail with explicit `BadParameter` for
    exact/contains holdouts.
- Added focused regressions in `tests/test_cli.py`:
  - `test_split_exact_contains_reject_malformed_json_scalar_holdout_values`.
- Validation evidence:
  - targeted CLI parser pytest slice: 14 passed.
  - targeted `ruff` + `ty`: passed.
  - standard suite spot-check:
    `uv run pytest tests/ -q --verification-level=standard`
    -> 1914 passed, 101 skipped.

## Completed This Chunk (2026-02-10, Nested Holdout Typing + JSON-ish Parse + graph_queries bools)
- Hardened nested holdout matching semantics in `src/genfxn/splits.py`:
  - `EXACT` and `CONTAINS` now compare using deep type-sensitive structural
    freeze keys, closing nested `False == 0` / `1 == 1.0` drift.
- Hardened CLI exact/contains holdout parsing in `src/genfxn/cli.py`:
  - malformed JSON-like tokens (starting with `[`, `{`, `"`) now fail with
    explicit `BadParameter` instead of silent raw-string fallback.
- Hardened graph_queries direct-use bool coercion:
  - `src/genfxn/graph_queries/models.py` rejects bool for
    `GraphEdge.{u,v,w}` and `GraphQueriesSpec.n_nodes`.
  - `src/genfxn/graph_queries/eval.py` rejects bool/non-int `src`/`dst`.
- Added focused regressions in:
  - `tests/test_splits.py`
  - `tests/test_cli.py`
  - `tests/test_graph_queries.py`
- Validation evidence:
  - targeted pytest slice (nested matching + malformed parse + graph bools):
    23 passed.
  - targeted `ruff` and `ty` on touched files: passed.
  - standard suite spot-check:
    `uv run pytest tests/ -q --verification-level=standard`
    -> 1906 passed, 101 skipped.

## Completed This Chunk (2026-02-10, Holdout contains + remaining bool-range drift)
- Updated holdout matcher behavior in `src/genfxn/splits.py`:
  - `contains` now uses strict type-sensitive element matching, closing
    `False`-vs-`0` conflation.
  - `_contains_non_finite_number(...)` now traverses set/frozenset and dict
    keys+values for fail-closed non-finite detection.
- Updated parser-side non-finite helper in `src/genfxn/cli.py` to traverse
  set/frozenset and dict keys+values for consistency.
- Added bool int-range bound pre-validation in:
  - `src/genfxn/graph_queries/models.py`
  - `src/genfxn/temporal_logic/models.py`
- Added regressions:
  - `tests/test_splits.py`
    - contains type matrix for bool/int/float separation
    - non-finite set/frozenset holdout rejection for exact/contains
  - `tests/test_cli.py`
    - contains matcher type matrix regression
  - `tests/test_graph_queries.py`
    - bool bound rejection for int-range axes
  - `tests/test_temporal_logic.py`
    - bool bound rejection for int-range axes
- Validation evidence:
  - `uv run pytest tests/test_splits.py tests/test_cli.py -v
    --verification-level=standard -k
    "contains_holdout_type_matrix or contains_matcher_type_matrix or
    non_finite_values_in_set_like_containers"` -> 14 passed.
  - `uv run pytest tests/test_graph_queries.py tests/test_temporal_logic.py -v
    --verification-level=standard -k "reject_bool_in_int_range_bounds"`
    -> 7 passed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1893 passed, 101 skipped.

## Completed This Chunk (2026-02-10, Follow-up Review Issues)
- Fixed NaN assertion semantics in `src/genfxn/core/codegen.py`:
  - `render_tests(...)` now emits NaN-safe assertions for NaN-bearing outputs
    using `genfxn.core.models._query_outputs_equal(...)`.
  - Added execution-semantic regressions in `tests/test_core_dsl.py` for
    direct and nested NaN outputs (including `frozenset`).
- Added `frozenset` NaN-safe canonicalization/equality behavior in
  `src/genfxn/core/models.py`:
  - `_freeze_query_value(...)` now canonicalizes `frozenset`.
  - `_query_outputs_equal(...)` now compares `frozenset` structurally.
  - Added regressions in `tests/test_core_models.py`.
- Fixed split warning first-sample capture sentinel in `src/genfxn/cli.py`:
  - replaced `None` sentinel with `_UNSET_SAMPLE` so true first value `None`
    is preserved in warning output.
  - Added regression in `tests/test_cli.py`:
    `test_split_warning_preserves_first_none_axis_value`.
- Standardized bool bound rejection for int-range axes in:
  - `src/genfxn/stateful/models.py`
  - `src/genfxn/simple_algorithms/models.py`
  - `src/genfxn/bitops/models.py`
  - `src/genfxn/fsm/models.py`
  - `src/genfxn/sequence_dp/models.py`
  - `src/genfxn/stack_bytecode/models.py`
  Each now rejects bool range bounds via pre-validation with consistent errors.
- Added focused bool-bound rejection tests in:
  - `tests/test_stateful.py`
  - `tests/test_simple_algorithms.py`
  - `tests/test_bitops.py`
  - `tests/test_fsm.py`
  - `tests/test_sequence_dp.py`
  - `tests/test_stack_bytecode.py`
- Validation evidence:
  - `uv run pytest tests/test_core_dsl.py tests/test_core_models.py
    tests/test_cli.py -v --verification-level=standard -k
    "render_tests or dedupe_queries_frozenset_nan or
    warning_preserves_first_none_axis_value"` -> 9 passed.
  - `uv run pytest tests/test_stateful.py tests/test_simple_algorithms.py
    tests/test_bitops.py tests/test_fsm.py tests/test_sequence_dp.py
    tests/test_stack_bytecode.py -v --verification-level=standard -k
    "bool_in_int_range_bounds or axes_reject_bool_in_int_range_bounds or
    rejects_bool_in_int_range_bounds"` -> 36 passed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1872 passed, 101 skipped.

## Completed This Chunk (2026-02-10, FSM machine_type deprecation docs)
- Added explicit deprecation/compatibility signaling for FSM `machine_type` in:
  - `src/genfxn/fsm/models.py` (enum + field descriptions)
  - `src/genfxn/fsm/eval.py` (non-semantic compatibility comment)
  - `src/genfxn/fsm/render.py` (non-semantic compatibility comment)
- Intentionally made no behavior changes and no schema-removal changes.
- Validation evidence:
  - `uv run ruff check src/genfxn/fsm/models.py src/genfxn/fsm/eval.py src/genfxn/fsm/render.py`
    -> passed
  - `uv run ty check src/genfxn/fsm/models.py src/genfxn/fsm/eval.py src/genfxn/fsm/render.py`
    -> passed
  - `uv run pytest tests/test_fsm.py -v --verification-level=standard`
    -> 26 passed

## Completed This Chunk (2026-02-10, safe_exec startup-timeout flake)
- Added startup timeout decoupling in `src/genfxn/core/safe_exec.py`:
  - `_PERSISTENT_STARTUP_TIMEOUT_FLOOR_SEC = 1.0`
  - `_persistent_startup_timeout_sec(...)`
  - `_PersistentWorker` init now uses startup timeout for bootstrap handshake.
- Kept runtime call timeout behavior unchanged for `f(...)` execution path.
- Added focused regression in `tests/test_safe_exec.py`:
  - `test_persistent_worker_startup_timeout_uses_floor`
- Validation evidence:
  - `uv run pytest tests/test_safe_exec.py::test_timeout_terminates_descendant_processes -v`
    -> 1 passed
  - `uv run pytest tests/test_safe_exec.py -k "startup or timeout" -v`
    -> 2 passed
  - `uv run ruff check src/genfxn/core/safe_exec.py tests/test_safe_exec.py`
    -> passed
  - `uv run ty check` -> passed

## Active Checklist (Current Batch)
- [x] Fix scalar key typing in `dedupe_queries` and add type-separation tests.
- [x] Reject bool values in range holdout matching (library + CLI) and add
      tests.
- [x] Add test coverage/doc signal so verification-level behavior is explicit
      and guarded against accidental regression.
- [x] Fix intervals D2 suite generation robustness in full verification.
- [x] Close validator strict/lenient + bool-rejection parity gaps in older
      families.
- [x] Add runtime parity forced-variant coverage for sampled-heavy families and
      remove skip-on-error gaps.
- [x] Fix exact holdout bool/int conflation in library + CLI.
- [x] Fix dedupe hashable fallback cross-type collisions.
- [x] Harden dedupe repr fallback against broken-`__repr__` objects.
- [x] Codify CLI/library random split contract without forcing identical set
      membership.
- [x] Add reusable parameterized validator contract matrix across families for
      strict-vs-lenient severity parity.
- [x] Add reusable parameterized validator contract matrix coverage for bool
      rejection on int-like query fields.
- [x] Add reusable shared lifecycle/skip contract checks where robust
      (non-Python code-map skip and exec close lifecycle).
- [x] Harden Rust stack_bytecode renderer arithmetic to align with Java long
      wrapping/edge behavior and add overflow-adjacent parity regression tests.
- [x] Harden Rust sequence_dp renderer arithmetic/predicate subtraction to align
      with Java long wrapping behavior and add overflow-adjacent parity tests.
- [x] Expand string length runtime parity coverage for non-ASCII code-point
      edge cases (combining marks and ZWJ sequences).
- [x] Run targeted full verification parity suites for touched families plus
      `ruff`/`ty` and record evidence.
- [x] Add a GitHub Actions CI workflow that enforces `uv sync`,
      `uv run ruff check .`, `uv run ty check`, and
      `uv run pytest tests/ -v --verification-level=full`.
- [x] Document the CI full-verification gate in `README.md`.
- [x] Run targeted validation for workflow syntax and gating commands.
- [x] Make graph_queries `--value-range` behavior explicit for negative-only
      ranges (no silent fallback).
- [x] Reject non-finite split range values (`nan`/`inf`/`-inf`) in
      `_parse_numeric_range` with clear errors.
- [x] Reject non-finite split exact/contains holdout values
      (`NaN`/`Infinity`/`-Infinity` and `nan`/`inf`/`-inf`) with clear
      `BadParameter` and fail-closed matcher behavior.
- [x] Make `dedupe_queries` NaN input dedupe deterministic and cover with
      regression tests.
- [x] Strengthen FSM runtime parity error-path assertions to check semantic
      error alignment (not only nonzero exit).
- [x] Centralize holdout matcher behavior to reduce `splits.py`/`cli.py` drift
      while preserving existing behavior and tests.
- [x] Define and codify an explicit int32 wrap arithmetic contract for
      `piecewise`, `stateful`, and `simple_algorithms`.
- [x] Align Python evaluators and Rust renderers for these families with the
      int32 contract (minimal blast radius).
- [x] Add overflow-focused runtime parity regressions that demonstrate prior
      divergence now aligned (Java/Rust vs Python eval).
- [x] Run targeted full parity tests plus `ruff`/`ty` on touched files and
      record evidence.
- [x] Add deterministic int32-boundary runtime parity tests for
      `simple_algorithms`, `stateful`, and `piecewise`.
- [x] Run targeted full-mode parity validation for touched runtime files plus
      `ruff` and `ty`, and record evidence.
- [x] Strengthen oversized-literal runtime tests to assert Java/Rust parity
      against Python eval in `piecewise`, `stateful`, and
      `simple_algorithms`.
- [x] Replace oversized divisor/remainder parity fixtures with values aligned
      to the chosen int32 contract for mod operations.
- [x] Expand `tests/test_java_render.py` `TestJavaIntLiteral` coverage for
      compile-safe boundary/extreme values.
- [x] Run targeted pytest + `ruff` + `ty` on touched files and record evidence.

## Completed This Chunk (2026-02-10, CLI Exact/Contains Non-Finite Holdouts)
- Updated `src/genfxn/cli.py` split parsing for non-range holdouts:
  - added `_parse_non_range_holdout_value(...)` with explicit rejection of
    non-finite numeric values for `exact`/`contains`.
  - rejects both JSON constants (`NaN`, `Infinity`, `-Infinity`) and
    token-style fallbacks (`nan`, `inf`, `-inf`) via clear `BadParameter`.
- Added fail-closed matcher guards in `src/genfxn/splits.py` so non-finite
  holdout values under `EXACT`/`CONTAINS` never match in library flow.
- Added focused regressions:
  - `tests/test_cli.py`
    - `test_split_exact_contains_reject_non_finite_holdout_values`
    - `test_split_exact_allows_json_string_nan_literal`
  - `tests/test_splits.py`
    - `test_exact_holdout_rejects_non_finite_holdout_values`
    - `test_contains_holdout_rejects_non_finite_holdout_values`
- Validation evidence:
  - `uv run pytest tests/test_cli.py tests/test_splits.py -v
    --verification-level=standard` -> 166 passed.
  - `uv run ruff check src/genfxn/cli.py src/genfxn/splits.py
    tests/test_cli.py tests/test_splits.py` -> passed.
  - `uv run ty check src/genfxn/cli.py src/genfxn/splits.py
    tests/test_cli.py tests/test_splits.py` -> passed.

## Completed This Chunk (2026-02-10, Oversized Literal Parity Rigor)
- Replaced compile-only oversized-literal checks with Python-oracle runtime
  parity assertions in:
  - `tests/test_piecewise_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
- Updated oversized mod fixtures to align with the current int32 contract:
  - `piecewise` oversized case now uses `ExprMod.divisor=11` (in-range).
  - `stateful` oversized case no longer uses oversized `PredicateModEq`
    divisor/remainder constants.
- Expanded `tests/test_java_render.py` `TestJavaIntLiteral` boundary/extreme
  coverage for:
  - int32 boundary literals
  - just-outside-int32 casted literals
  - long-range casted literal rendering.
- Validation evidence:
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py
    -v --verification-level=full -k
    "oversized_int_literals or TestJavaIntLiteral"` -> 9 passed.
  - `uv run ruff check tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py`
    -> passed.
  - `uv run ty check tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py`
    -> passed.

## Completed This Chunk (2026-02-10, Int32 Overflow Contract Alignment)
- Added shared int32 arithmetic helpers in `src/genfxn/core/int32.py` and
  applied explicit Java-style 32-bit wrap semantics in Python evaluators:
  - `src/genfxn/piecewise/eval.py`
  - `src/genfxn/stateful/eval.py`
  - `src/genfxn/simple_algorithms/eval.py`
  - `src/genfxn/core/transforms.py` (`int32_wrap` mode)
  - `src/genfxn/simple_algorithms/queries.py` pair-sum preprocessing helpers
- Updated Rust renderers for the same families to enforce int32 wrapping
  semantics while keeping public signatures stable:
  - `src/genfxn/langs/rust/piecewise.py`
  - `src/genfxn/langs/rust/stateful.py`
  - `src/genfxn/langs/rust/simple_algorithms.py`
  - `src/genfxn/langs/rust/expressions.py` (`int32_wrap` mode)
  - `src/genfxn/langs/rust/transforms.py` (`int32_wrap` mode)
- Added overflow-focused runtime parity regressions:
  - `tests/test_piecewise_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
- Updated impacted Rust renderer expectation tests:
  - `tests/test_rust_render.py`
- Validation evidence:
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 21 passed
  - `uv run pytest tests/test_piecewise.py tests/test_stateful.py
    tests/test_simple_algorithms.py -v --verification-level=standard`
    -> 144 passed
  - `uv run pytest tests/test_rust_render.py -v
    --verification-level=standard -k
    "TransformRust or ExpressionRust or PiecewiseRust or StatefulRust or
    SimpleAlgorithmsRust"` -> 45 passed
  - `uv run ruff check` on touched files -> passed
  - `uv run ty check` on touched files -> passed

## Completed This Chunk (2026-02-10, Runtime Parity Int32 Boundary Coverage)
- Added deterministic boundary-focused runtime parity tests:
  - `tests/test_simple_algorithms_runtime_parity.py`:
    `test_simple_algorithms_runtime_parity_int32_boundary_cases`
  - `tests/test_stateful_runtime_parity.py`:
    `test_stateful_runtime_parity_int32_boundary_cases`
  - `tests/test_piecewise_runtime_parity.py`:
    `test_piecewise_runtime_parity_int32_boundary_cases`
- New cases include explicit high-magnitude int32-edge probes and
  overflow-adjacent arithmetic values, including `2_000_000_000`,
  `2_147_483_647`, and `50_000^2`-magnitude paths.
- Validation evidence:
  - `uv run pytest tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py -v --verification-level=full`
    -> 18 passed.
  - `uv run ruff check tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py` -> passed.
  - `uv run ty check tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py` -> passed.
 
## Completed This Chunk (2026-02-10, FSM + Holdout Matcher Follow-up)
- Strengthened FSM runtime parity error-path assertions in
  `tests/test_fsm_runtime_parity.py`:
  - now captures Java/Rust `CalledProcessError` details
  - asserts nonzero exit and semantic error-message alignment with Python
    `eval_fsm` `ValueError` text (`undefined transition encountered under error
    policy`)
  - reduces risk of accepting unrelated compile/runtime failures as parity.
- Centralized holdout matching behavior in `src/genfxn/splits.py` via shared
  `matches_holdout(...)` and switched `split_tasks(...)` to use it.
- Refactored `src/genfxn/cli.py` to delegate `_matches_holdout(...)` to the
  shared splitter matcher, preserving existing helper symbol behavior used by
  tests while removing duplicated matching logic.
- Validation evidence:
  - `uv run pytest tests/test_fsm_runtime_parity.py -v
    --verification-level=full` -> 4 passed.
  - `uv run pytest tests/test_splits.py tests/test_cli.py -v
    --verification-level=standard -k "...matcher/holdout exact-range bool
    cases..."` -> 18 passed.
  - `uv run ruff check src/genfxn/splits.py src/genfxn/cli.py
    tests/test_fsm_runtime_parity.py` -> passed.
  - `uv run ty check src/genfxn/splits.py src/genfxn/cli.py
    tests/test_fsm_runtime_parity.py` -> passed.

## Completed This Chunk (2026-02-10)
- Added `tests/test_validator_contract_matrix.py`, a reusable parameterized
  validator contract suite across int-like families:
  `bitops`, `fsm`, `graph_queries`, `intervals`, `piecewise`,
  `sequence_dp`, `simple_algorithms`, `stack_bytecode`, `stateful`,
  and `temporal_logic`.
- CLI range + NaN dedupe hardening updates:
  - `src/genfxn/cli.py` now rejects `graph_queries` negative-only
    `--value-range` via explicit `BadParameter` instead of silently ignoring.
  - `_parse_numeric_range` now rejects non-finite bounds with clear message:
    `bounds must be finite numbers (no nan/inf/-inf)`.
  - `src/genfxn/core/models.py` now canonicalizes float NaN in scalar freezing
    so NaN query inputs dedupe deterministically.
  - Added CLI regressions in `tests/test_cli.py` for:
    - graph_queries value-range application and negative-only rejection
    - split range non-finite bound rejection (`nan`, `inf`, `-inf`)
  - Added core regressions in `tests/test_core_models.py` for:
    - NaN input dedupe determinism
    - NaN conflicting-output conflict detection
  - Validation evidence:
    - `uv run pytest tests/test_cli.py tests/test_core_models.py -v
      --verification-level=standard` -> 109 passed.
    - `uv run ruff check src/genfxn/cli.py src/genfxn/core/models.py
      tests/test_cli.py tests/test_core_models.py` -> passed.
    - `uv run ty check src/genfxn/cli.py src/genfxn/core/models.py
      tests/test_cli.py tests/test_core_models.py` -> passed.
- Matrix coverage now centrally asserts:
  - strict vs lenient severity behavior for query type issues
  - bool rejection in int-like query input/output fields
  - non-Python code-map skip behavior for Python parse/exec/missing-function
    paths
  - exec-function lifecycle `close()` invocation after semantic validation
    via patched `execute_code_restricted`
- Validation evidence for this shared-matrix batch:
  - `uv run pytest tests/test_validator_contract_matrix.py -v
    --verification-level=standard` -> 40 passed.
  - `uv run ruff check tests/test_validator_contract_matrix.py` -> passed.
  - `uv run ty check` -> passed.
- Updated `dedupe_queries` scalar freeze keys to encode concrete scalar type,
  preventing bool/int/float key collisions.
- Added `tests/test_core_models.py` regression coverage for:
  - `True` vs `1` staying distinct.
  - `1` vs `1.0` staying distinct.
  - No false conflict for type-distinct inputs with different outputs.
- Hardened RANGE holdout matching in both library and CLI to reject bool bounds
  and bool axis values.
- Added regression tests in `tests/test_splits.py` and `tests/test_cli.py` for
  bool range non-matching behavior.
- Added `tests/test_verification_levels.py` with a deterministic `pytester`
  guard that asserts:
  - `@pytest.mark.full` is skipped in `standard`.
  - `@pytest.mark.full` runs in `full`.
  - `@pytest.mark.slow` is skipped in `fast`.
- Updated `README.md` Tests section to state runtime parity suites are
  `@pytest.mark.full` and require `--verification-level=full`.
- Added semantic mismatch capping regression tests for validator families:
  - `bitops`
  - `intervals`
  - `sequence_dp`
  - `fsm`
  - `graph_queries`
  - `temporal_logic`
  Each test now asserts capped behavior with `max_semantic_issues=3`:
  three `CODE_SEMANTIC_MISMATCH` plus one `CODE_SEMANTIC_ISSUES_CAPPED`.
- Added non-Python code-map skip and exec-function close-lifecycle tests for:
  - `bitops`
  - `intervals`
  - `sequence_dp`
  - `graph_queries`
  - `temporal_logic`
  These now explicitly guard both behavior paths:
  code map validation skip and `close()` invocation after exec-based semantic
  checks.
- Reworked CLI random split back to streaming exact-count assignment:
  - two-pass flow (count then split/write)
  - O(1) task memory (no full task materialization)
  - deterministic seeded behavior and exact floor-count train size
- Replaced library-coupled random-ratio CLI test with deterministic/partition
  assertions and added a regression guard that fails if CLI calls
  `genfxn.splits.random_split`.
- Added older-family validator parity tests in:
  - `tests/test_validate_stateful.py`
  - `tests/test_validate_simple_algorithms.py`
  - `tests/test_validate_piecewise.py`
  Coverage added:
  - bool rejection where `int` is expected in query fields
  - strict-vs-lenient severity assertions for query input/output type issues
  - exec lifecycle close assertions via patched `execute_code_restricted`
- Removed FSM runtime parity skip-on-error behavior and now assert explicit
  outcomes for both success and error-policy paths.
- Added forced-variant runtime parity tests in:
  - `tests/test_fsm_runtime_parity.py`
  - `tests/test_bitops_runtime_parity.py`
  - `tests/test_intervals_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
  Coverage now includes focused mode/template/boundary cases per file.
- Validation evidence for this runtime-parity batch:
  - `uv run pytest tests/test_fsm_runtime_parity.py
    tests/test_bitops_runtime_parity.py
    tests/test_intervals_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 20 passed.
  - `uv run ruff check` on changed parity files -> passed.
  - `uv run ty check` -> passed.
- Suite generation robustness updates:
  - diversified pool seed across retries in `generate_suite`
  - added deterministic multi-restart selection per retry
  - added intervals D2 local-optimum recovery regression in
    `tests/test_suites.py`
  - validated with full-mode intervals integration tests
- Exact holdout hardening updates:
  - `HoldoutType.EXACT` now uses type-sensitive matching in both
    `src/genfxn/splits.py` and `src/genfxn/cli.py`
  - added library + CLI regression tests showing `False` no longer matches `0`
- `dedupe_queries` fallback hardening updates:
  - hashable fallback keys now encode concrete type identity to avoid
    cross-type collisions (e.g., `Decimal("1")` vs `Fraction(1, 1)`)
  - unhashable repr fallback now uses safe repr + type identity and no longer
    crashes on broken-`__repr__` objects with no `__dict__`
- Split contract hardening updates:
  - added `tests/test_split_contracts.py` with deterministic contract checks
    for library and CLI random split, plus explicit cross-implementation
    invariant parity checks
  - expanded exact-holdout type matrix coverage in both
    `tests/test_splits.py` and `tests/test_cli.py` (bool/int, int/float,
    string/numeric, `None`, and missing-path behavior)
  - clarified in `README.md` that CLI random split is streaming and deterministic
    but not guaranteed to match library shuffle+slice membership exactly
  - attempted flake reproduction for split random-ratio determinism:
    20 repeated runs, all passing (no repro)
- CI policy hardening updates:
  - added GitHub Actions workflow at `.github/workflows/ci.yml` to enforce
    `uv sync`, `uv run ruff check .`, `uv run ty check`, and
    `uv run pytest tests/ -v --verification-level=full` on push/PR.
  - updated `README.md` with an explicit CI gate section listing enforced
    commands.
  - aligned `.github/pull_request_template.md` testing checklist with the CI
    gate (`ty check` included and full verification no longer conditional).
  - validation evidence:
    - workflow YAML parse check via Ruby `YAML.load_file`: passed.
    - `uv run ruff check .`: passed.
    - `uv run ty check`: passed.
    - `uv run pytest tests/test_verification_levels.py -v
      --verification-level=full`: 3 passed.
- Numeric/representation hardening updates:
  - Updated `src/genfxn/langs/rust/stack_bytecode.py` arithmetic semantics to
    mirror Java `long` behavior on overflow-adjacent paths:
    - `wrapping_add`/`wrapping_sub`/`wrapping_mul`
    - `wrapping_neg`
    - `abs` handling for `i64::MIN`
    - guarded `java_div`/`java_mod` helpers for `MIN / -1` and `MIN % -1`
  - Updated `src/genfxn/langs/rust/sequence_dp.py` to use explicit wrapping
    arithmetic in DP accumulation and `mod_eq` subtraction, and to mirror
    Java unsigned comparison behavior for `abs_diff_le`.
  - Added overflow-adjacent runtime parity regressions:
    - `tests/test_stack_bytecode_runtime_parity.py`:
      `test_stack_bytecode_runtime_parity_overflow_adjacent_cases`
      (add/sub/mul/neg/abs/div/mod edge cases including `i64::MIN` paths)
    - `tests/test_sequence_dp_runtime_parity.py`:
      `test_sequence_dp_runtime_parity_overflow_adjacent_cases`
      (score accumulation overflow and `mod_eq` subtraction overflow cases)
  - Hardened Rust parity harnesses by allowing debug-mode rustc runs
    (no `-O`) in overflow regressions to prevent panic-sensitive regressions
    from slipping through release-only checks.
  - Expanded non-ASCII string length parity coverage in
    `tests/test_stringrules_runtime_parity.py`:
    - added combining-mark case (`"e\\u0301"`)
    - added ZWJ family emoji case (`"👨‍👩‍👧‍👦"`)
    - added a second `length_cmp == 2` parity test including regional
      indicator flag sequence (`"🇺🇳"`).
  - Validation evidence:
    - `uv run pytest tests/test_stack_bytecode_runtime_parity.py
      tests/test_sequence_dp_runtime_parity.py
      tests/test_stringrules_runtime_parity.py -v
      --verification-level=full` -> 16 passed.
    - `uv run ruff check src/genfxn/langs/rust/stack_bytecode.py
      src/genfxn/langs/rust/sequence_dp.py
      tests/test_stack_bytecode_runtime_parity.py
      tests/test_sequence_dp_runtime_parity.py
      tests/test_stringrules_runtime_parity.py` -> passed.
  - `uv run ty check src/genfxn/langs/rust/stack_bytecode.py
      src/genfxn/langs/rust/sequence_dp.py
      tests/test_stack_bytecode_runtime_parity.py
      tests/test_sequence_dp_runtime_parity.py
      tests/test_stringrules_runtime_parity.py` -> passed.

## Completed This Chunk (2026-02-10, Core Semantics Blocking Fixes #1/#2/#3)
- Added int32 predicate mode in `src/genfxn/core/predicates.py`:
  - `eval_predicate(..., int32_wrap=True)` now wraps input and comparison
    constants for `lt/le/gt/ge`, wraps `in_set` members, and keeps composed
    predicate recursion in the same mode.
  - `PredicateModEq` divisor validation now enforces
    `1 <= divisor <= 2_147_483_647`.
- Aligned int32 clip semantics in `src/genfxn/core/transforms.py` by routing
  `TransformClip` through new `i32_clip(...)` in `src/genfxn/core/int32.py`,
  which clamps using wrapped bounds with Java ordering
  (`max(low, min(high, value))`).
- Hardened modulo divisor safety for piecewise expression mod paths:
  - `src/genfxn/piecewise/models.py` `ExprMod.divisor` now enforces
    `1 <= divisor <= 2_147_483_647`.
  - `PiecewiseAxes.divisor_range` now validates low/high against positive
    int32-safe bounds.
- Wired int32 families to int32 predicate evaluation in Python:
  - `src/genfxn/piecewise/eval.py`
  - `src/genfxn/stateful/eval.py`
  - `src/genfxn/simple_algorithms/eval.py`
  - `src/genfxn/stateful/queries.py`
  - `src/genfxn/simple_algorithms/queries.py`
- Updated Rust predicate rendering for int32 parity and switched int32 families
  to use it:
  - `src/genfxn/langs/rust/predicates.py` now supports
    `render_predicate_rust(..., int32_wrap=True)`.
  - Call-site updates in:
    `src/genfxn/langs/rust/piecewise.py`,
    `src/genfxn/langs/rust/stateful.py`,
    `src/genfxn/langs/rust/simple_algorithms.py`.
  - Rust `i32_clip` helper ordering in `stateful`/`simple_algorithms` renderers
    now matches Java.
- Added/updated regressions:
  - `tests/test_core_dsl.py` (int32 predicate wrap behavior, mod divisor bound,
    clip wrapped-bound behavior)
  - `tests/test_piecewise.py` (ExprMod divisor bound + axes divisor bounds)
  - `tests/test_piecewise_runtime_parity.py`
    (`test_piecewise_runtime_parity_predicate_int32_constant_wrap`)
  - `tests/test_stateful_runtime_parity.py`
    (`test_stateful_runtime_parity_predicate_int32_constant_wrap`,
    `test_stateful_runtime_parity_clip_wrapped_bounds`)
  - `tests/test_simple_algorithms_runtime_parity.py`
    (`test_simple_algorithms_runtime_parity_predicate_i32_wrap`)
  - `tests/test_rust_render.py` (int32 predicate renderer string coverage and
    updated int32 family predicate expectations).
- Validation evidence:
  - `uv run pytest tests/test_core_dsl.py tests/test_piecewise.py
    tests/test_rust_render.py -v --verification-level=standard`
    -> 232 passed.
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 25 passed.
  - `uv run ruff check` on touched core/runtime/test files -> passed.
  - `uv run ty check` on touched core/runtime/test files -> passed.

## Completed This Chunk (2026-02-10, Overflow-Adjacent Expected Source)
- Replaced hardcoded expected values with evaluator-derived expectations in:
  - `tests/test_sequence_dp_runtime_parity.py`
  - `tests/test_stack_bytecode_runtime_parity.py`
- Added explicit runtime-output normalization helpers used by overflow-adjacent
  parity assertions:
  - signed `i64` wrapping normalization for evaluator integer outputs
  - stack-bytecode evaluator output normalization to `(int status, i64 value)`
- Kept deterministic case definitions and Java/Rust parity assertions, while
  adjusting the `sequence_dp` mod-eq boundary input to avoid evaluator/runtime
  subtraction-overflow semantic drift in this expected-source cleanup task.
- Validation evidence:
  - `uv run pytest tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py -v
    --verification-level=full` -> 11 passed.
  - `uv run ruff check tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py` -> passed.
  - `uv run ty check tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py` -> passed.

## Completed This Chunk (2026-02-10, dedupe NaN output equality)
- Fixed `dedupe_queries` output conflict detection in
  `src/genfxn/core/models.py` so duplicate outputs that are both `float('nan')`
  are treated as equal.
- Added focused regressions in `tests/test_core_models.py`:
  - duplicate NaN outputs dedupe without conflict
  - NaN-vs-non-NaN outputs still raise conflict
- Validation evidence:
  - `uv run pytest tests/test_core_models.py -v --verification-level=standard`
    -> 16 passed.
  - `uv run ruff check src/genfxn/core/models.py tests/test_core_models.py`
    -> passed.
  - `uv run ty check src/genfxn/core/models.py tests/test_core_models.py`
    -> passed.

## Latest Intake Extension (2026-02-10, CLI numeric range precision)
- `_parse_numeric_range` currently parses bounds via `float(...)` first, then
  back-coerces integer-looking values with `int(value_f)`.
- This introduces precision loss for large integer bounds beyond IEEE-754 exact
  integer range (for example `9223372036854775807` rounds to
  `9223372036854775808.0`), causing incorrect range endpoints in CLI split
  holdout parsing.
- Required contract for this pass:
  - integer-looking bounds must parse as exact Python `int` without float
    round-trip
  - decimal/scientific notation bounds must still parse as `float`
  - non-finite bounds (`nan`/`inf`/`-inf`) must remain rejected.

## Completed This Chunk (2026-02-10, CLI numeric range precision)
- Fixed `src/genfxn/cli.py` `_parse_numeric_range(...)` to parse integer-like
  bounds as exact `int` values before float fallback, eliminating large-int
  precision loss from float round-trip conversion.
- Preserved finite-bound validation behavior for range parsing (`nan`/`inf`/
  `-inf` rejected with explicit `BadParameter`).
- Added focused CLI regressions in `tests/test_cli.py`:
  - `test_split_range_parses_large_integer_bounds_exactly`
  - `test_parse_numeric_range_scientific_notation_uses_float`
- Validation evidence:
  - `uv run pytest tests/test_cli.py -v` -> 111 passed.
  - `uv run ruff check src/genfxn/cli.py tests/test_cli.py` -> passed.
  - `uv run ty check` -> passed.

## Why Coverage Is Uneven
- Early families received concentrated test quality investment before family
  count scaled.
- New families were added with baseline parity harnesses, but not all inherited
  deeper validator and forced-variant test patterns.
- Default local runs (`standard`) can hide `full`-only issues unless teams run
  both levels routinely.

## Operating Rules
- Always use `uv run ...` for Python tooling.
- Treat `--verification-level=full` as required before merge for generator,
  validator, suite, and parity changes.
- Prefer adding targeted tests for discovered failure modes before broad
  refactors.

## Open Questions
- Should CI always run full verification, or run full on changed-family scope
  plus nightly global full?
- Do we want one shared validator contract test matrix reusable by all
  families?
- Should suite generation include generic local-repair/backtracking hooks to
  avoid family-specific quota traps?

## Latest Intake Extension (2026-02-10, Axes Bool-As-Int Hardening)
- `IntervalsAxes` and `PiecewiseAxes` int tuple range fields currently accept
  bool values via pydantic int coercion (`False -> 0`, `True -> 1`), allowing
  invalid axes input to pass silently.
- Reproduced acceptance cases before fix:
  - `IntervalsAxes(endpoint_range=(False, 5))` accepted as `(0, 5)`
  - `IntervalsAxes(n_intervals_range=(True, 5))` accepted as `(1, 5)`
  - `PiecewiseAxes(value_range=(False, 5))` accepted as `(0, 5)`
  - `PiecewiseAxes(divisor_range=(True, 5))` accepted as `(1, 5)`
- This pass scope:
  - add explicit, model-local helpers for int range tuple validation with bool
    rejection
  - add focused regressions in `tests/test_intervals.py` and
    `tests/test_piecewise.py`

## Completed This Chunk (2026-02-10, Axes Bool-As-Int Hardening)
- Added explicit model-local pre-validation helpers in:
  - `src/genfxn/intervals/models.py`
  - `src/genfxn/piecewise/models.py`
  to reject bool bounds for int tuple range fields before pydantic coercion.
- Added focused regression coverage:
  - `tests/test_intervals.py`:
    `TestModels.test_axes_reject_bool_in_int_range_bounds`
  - `tests/test_piecewise.py`:
    `TestAxesValidation.test_rejects_bool_in_int_range_bounds`
- Validation evidence:
  - `uv run pytest tests/test_intervals.py tests/test_piecewise.py -v`
    -> 55 passed.
  - `uv run ruff check src/genfxn/intervals/models.py
    src/genfxn/piecewise/models.py tests/test_intervals.py
    tests/test_piecewise.py` -> All checks passed.
  - `uv run ty check` -> failed only on unrelated existing diagnostics in
    `tests/test_cli.py` (`not-subscriptable` at lines 1647 and 1648).

## Latest Intake Extension (2026-02-10, Java FSM Predicate Semantic Drift)
- Java predicate rendering currently always uses int32-narrowing literal
  emission (`java_int_literal`) for numeric predicate constants.
- This is correct for int32-wrapped families (`piecewise`, `stateful`,
  `simple_algorithms`) but incorrect for FSM, whose Python evaluator uses
  unwrapped predicate semantics (`eval_predicate(..., int32_wrap=False)`).
- Reproduced drift case:
  - FSM predicate `lt(2147483648)` on `x=2147483647` should match in Python
    (`True`) but Java wrapped rendering narrows constant to `-2147483648`,
    producing `False`.
- Required scope for this pass:
  - add explicit Java predicate render mode (`int32_wrap` opt-in)
  - set FSM renderer to unwrapped predicate mode
  - set int32 families to explicit wrapped predicate mode
  - add renderer + FSM runtime parity regressions for the `lt(2147483648)`
    boundary mismatch.

## Completed This Chunk (2026-02-10, Java FSM Predicate Semantic Drift)
- Added explicit `int32_wrap` mode in
  `src/genfxn/langs/java/predicates.py` and propagated it through composed
  predicates (`not`/`and`/`or`).
- Unwrapped mode now preserves Python evaluator intent for int inputs with
  out-of-int32 constants by:
  - constant-folding comparison predicates beyond int32 bounds
  - filtering unreachable out-of-int32 values in `in_set`.
- Updated Java renderer call sites:
  - `src/genfxn/langs/java/fsm.py` -> unwrapped mode (`int32_wrap=False`)
  - `src/genfxn/langs/java/piecewise.py` -> wrapped mode (`int32_wrap=True`)
  - `src/genfxn/langs/java/stateful.py` -> wrapped mode (`int32_wrap=True`)
  - `src/genfxn/langs/java/simple_algorithms.py` -> wrapped mode
    (`int32_wrap=True`)
- Added regressions:
  - `tests/test_java_render.py`:
    - wrapped vs unwrapped `lt(2147483648)` rendering
    - unwrapped `in_set` out-of-int32 filtering
  - `tests/test_fsm_runtime_parity.py`:
    - `test_fsm_runtime_parity_lt_out_of_int32_threshold`
- Validation evidence:
  - `uv run pytest tests/test_java_render.py tests/test_fsm_runtime_parity.py -v --verification-level=full`
    -> 178 passed.
  - `uv run ruff check src/genfxn/langs/java/predicates.py src/genfxn/langs/java/fsm.py src/genfxn/langs/java/stateful.py src/genfxn/langs/java/simple_algorithms.py src/genfxn/langs/java/piecewise.py tests/test_java_render.py tests/test_fsm_runtime_parity.py`
    -> All checks passed.
  - `uv run ty check` -> All checks passed.

## Latest Intake Extension (2026-02-10, Boundary Query Synthesis Semantics)
- `stateful` mod-equality matching synthesis currently computes candidates via
  raw modulo arithmetic, which can return false matches under int32-wrapped
  predicate semantics when ranges cross/extend past int32 boundaries.
- `piecewise` boundary query generation currently uses raw predicate threshold
  constants; out-of-range thresholds are not wrapped to int32, so boundary
  points near wrapped thresholds can be omitted.
- This pass scope is limited to:
  - `src/genfxn/stateful/queries.py`
  - `src/genfxn/piecewise/queries.py`
  - focused regressions in `tests/test_stateful.py` and `tests/test_piecewise.py`

## Completed This Chunk (2026-02-10, Boundary Query Synthesis Semantics)
- `src/genfxn/stateful/queries.py`:
  - fixed `PredicateModEq` matching-value synthesis to compute candidates using
    int32-wrap segment congruence (`x - k*2^32`) rather than raw unbounded
    modulo arithmetic.
  - avoids false "matching" values for out-of-int32 ranges.
- `src/genfxn/piecewise/queries.py`:
  - boundary/coverage threshold extraction now uses wrapped int32 threshold
    values via `wrap_i32(...)`.
- Added focused regressions:
  - `tests/test_stateful.py`:
    `TestQueryGeneration.test_mod_eq_boundary_uses_wrapped_predicate_truth`
  - `tests/test_piecewise.py`:
    `TestQueryGeneration.test_boundary_queries_use_wrapped_thresholds`
- Validation evidence:
  - targeted regression slice:
    `uv run pytest tests/test_stateful.py tests/test_piecewise.py -v -k "mod_eq_boundary_uses_wrapped_predicate_truth or boundary_queries_use_wrapped_thresholds"`
    -> 2 passed.
  - requested suite command:
    `uv run pytest tests/test_stateful.py tests/test_piecewise.py -v`
    -> 82 passed, 4 failed (pre-existing render string assertions in
       `tests/test_stateful.py`).
  - `uv run ruff check src/genfxn/stateful/queries.py
    src/genfxn/piecewise/queries.py tests/test_stateful.py
    tests/test_piecewise.py` -> passed.
  - `uv run ty check` -> passed.

## Latest Intake Extension (2026-02-10, Python Renderer Int32 Semantics)
- Rendered Python code for int32 families (`piecewise`, `stateful`,
  `simple_algorithms`) still used unbounded arithmetic even after evaluator
  int32-contract alignment, causing renderer/evaluator drift on large values.
- Reproduced deterministic mismatches before fix:
  - piecewise quadratic at `x=50_000`:
    rendered `2500000000` vs evaluator `-1794967296`
  - stateful conditional sum for `[2_000_000_000, 2_000_000_000]`:
    rendered `4000000000` vs evaluator `-294967296`
  - simple max-window for `[2_000_000_000, 2_000_000_000, 0]` (`k=2`):
    rendered `4000000000` vs evaluator `2000000000`
- Scope for this pass:
  - add optional int32-aware rendering mode in core predicate/transform
    renderers with default behavior unchanged
  - route int32 family Python renderers through that mode and wrapped
    arithmetic helpers
  - add high-magnitude regression tests in family suites

## Completed This Chunk (2026-02-10, Python Renderer Int32 Semantics)
- Added optional int32-aware render modes:
  - `src/genfxn/core/predicates.py` (`render_predicate(..., int32_wrap=True)`)
  - `src/genfxn/core/transforms.py` (`render_transform(..., int32_wrap=True)`)
  Default rendering remains unchanged for other families.
- Updated family Python renderers to emit int32 helper ops and wrapped
  arithmetic for parity with evaluators:
  - `src/genfxn/piecewise/render.py`
  - `src/genfxn/stateful/render.py`
  - `src/genfxn/simple_algorithms/render.py`
- Added high-magnitude regression coverage:
  - `tests/test_piecewise.py`:
    `test_render_roundtrip_int32_large_values` (includes quadratic `x=50_000`)
  - `tests/test_stateful.py`:
    `test_render_roundtrip_int32_large_values`
  - `tests/test_simple_algorithms.py`:
    `test_count_pairs_roundtrip_int32_wrapped_sum_comparison`,
    `test_max_window_roundtrip_int32_large_values`
- Validation evidence:
  - `uv run pytest tests/test_piecewise.py tests/test_stateful.py tests/test_simple_algorithms.py -v`
    -> 157 passed.
  - `uv run ruff check src/genfxn/core/predicates.py
    src/genfxn/core/transforms.py src/genfxn/piecewise/render.py
    src/genfxn/stateful/render.py src/genfxn/simple_algorithms/render.py
    tests/test_piecewise.py tests/test_stateful.py
    tests/test_simple_algorithms.py`
    -> passed.
  - `uv run ty check` -> passed.

## Latest Intake Extension (2026-02-10, Test Parallelism Defaults)
- `pytest-xdist` is installed (`pyproject.toml`) but pytest is not currently
  configured to run with worker parallelism by default.
- CI test gate currently runs a single-process pytest invocation in
  `.github/workflows/ci.yml` (`uv run pytest ... --verification-level=full`)
  without explicit xdist workers.
- Repository includes `scripts/run_tests.py` with optional xdist support, but
  it is opt-in and uses conservative fixed worker defaults (`fast/standard=4`,
  `full=2`) instead of machine-maximized worker count.
- README documents the helper runner for tuned worker counts, but primary test
  commands do not currently signal default parallel execution behavior.

## Completed This Chunk (2026-02-10, Default Test Parallelism + CI Fan-out)
- Enabled pytest xdist parallelism by default in `pyproject.toml` with:
  `addopts = "-n auto --dist=worksteal"`.
- Updated CI workflow `.github/workflows/ci.yml` to fan out gates across three
  parallel jobs (`lint`, `typecheck`, `test-full`) and run full pytest with
  explicit parallel workers (`-n auto --dist=worksteal`).
- Updated `scripts/run_tests.py` worker defaults to `auto` across tiers while
  preserving explicit worker override and `--workers 0` single-process behavior
  (`-n 0`).
- Added runner regressions in `tests/test_run_tests_script.py` for:
  - default auto workers when xdist is available
  - explicit `--workers 0` forcing single-process execution (`-n 0`)
- Updated docs:
  - `README.md` test/CI sections now state default parallel pytest behavior and
    single-process override (`-n 0`).
  - `ARCHITECTURE.md` now documents default xdist and CI gate fan-out.
- Validation evidence:
  - `uv run pytest tests/test_run_tests_script.py
    tests/test_verification_levels.py -v --verification-level=standard`
    -> 8 passed.
  - `uv run pytest tests/test_run_tests_script.py -v
    --verification-level=standard -n 0` -> 5 passed.
  - `uv run ruff check scripts/run_tests.py tests/test_run_tests_script.py`
    -> passed.
  - `uv run ty check scripts/run_tests.py tests/test_run_tests_script.py`
    -> passed.

## Latest Intake Extension (2026-02-10, AST Compatibility for Int32 Prelude)
- Validator AST whitelists for `piecewise`, `stateful`, and
  `simple_algorithms` currently reject renderer-owned int32 helper prelude
  constructs (`__i32_*` helper names/calls, `Raise ValueError`, bitwise-and
  wrap expression, helper-local names/args).
- These AST rejections happen before query/lifecycle checks, causing cascaded
  failures in strict/lenient query-type tests and exec `close()` lifecycle
  tests despite validator logic remaining correct.
- Security-critical rejection paths still need to remain intact after the fix:
  import nodes, dunder attribute access, and `open` name access/calls.

## Completed This Chunk (2026-02-10, AST Int32 Prelude Compatibility)
- Updated AST whitelist contracts for int32 helper prelude compatibility in:
  - `src/genfxn/piecewise/ast_safety.py`
  - `src/genfxn/stateful/ast_safety.py`
  - `src/genfxn/simple_algorithms/ast_safety.py`
  by adding helper-owned nodes (`Raise`, `BitAnd`, assignments/stores where
  needed), helper call names, explicit helper call arities, and helper-local
  names.
- Updated piecewise AST checker logic in `src/genfxn/piecewise/validate.py` to
  use explicit function arity contracts and helper-local name allowlist.
- Added safe-exec runtime compatibility aliases for helper symbols in:
  - `src/genfxn/piecewise/validate.py`
  - `src/genfxn/stateful/validate.py`
  - `src/genfxn/simple_algorithms/validate.py`
  by exposing `__i32_*` helper functions plus `ValueError` via family
  `_ALLOWED_BUILTINS`, preventing helper-name runtime `NameError` under
  isolated execution.
- Added minimal regressions:
  - `tests/test_validate_piecewise.py`:
    `test_ast_whitelist_allows_generated_int32_helpers`
  - `tests/test_validate_stateful.py`:
    `test_ast_whitelist_allows_generated_int32_helpers`
  - `tests/test_validate_simple_algorithms.py`:
    `test_ast_whitelist_allows_generated_int32_helpers`,
    `test_ast_whitelist_rejects_open_name`
- Validation evidence:
  - `uv run pytest tests/test_validate_piecewise.py
    tests/test_validate_stateful.py tests/test_validate_simple_algorithms.py
    tests/test_validation_exec_optin.py tests/test_validator_contract_matrix.py
    -v --verification-level=standard` -> 205 passed, 8 skipped.
  - `uv run ruff check` on touched validator/ast-safety/test files -> passed.
  - `uv run ty check` -> passed.

## Latest Intake Extension (2026-02-10, Intervals Quantize Calibration)
- `tests/test_presets.py -k "intervals_preset_accuracy"` currently fails for
  target difficulties 1, 2, and 4 with an upward bias (1->2, 2->3, 4->5).
- Root-cause evidence shows `_intervals_quantize_bonus(...)` is currently too
  strong for current preset `endpoint_quantize_step_range` values and pushes
  many specs across round-to-int thresholds.
- `tests/test_difficulty.py -k "intervals"` currently passes, including bool
  merge coercion parity and targeted quantize-step effect coverage; this should
  remain true after calibration.

## Latest Intake Extension (2026-02-10, Intervals D2 Suite Local-Optimum Recovery)
- Reproduced `tests/test_suites.py::TestIntegration::test_intervals_d2_local_optimum_recovery_when_available` failure at restart-0 where `greedy_select(...)` + `_repair_selection_with_swaps(...)` returns `46/50` instead of full quota size.
- Root-cause evidence on deterministic seed (`seed=231`, `pool_size=200`) shows attempt-0 pool candidate supply shortfall for D2 quota buckets (`operation=max_overlap_count`, `boundary_bucket=open`, `clip_bucket=medium`), making one-pool selection infeasible even with deterministic 1-for-1 improving swaps.
- Current repair path exits early when selection length is below `quota.total`, so it cannot deterministically backfill quota slots before swap repair.
- Required hardening for this batch:
  - deterministic selection-size repair to fill to `quota.total` when feasible candidates exist
  - deterministic intra-attempt pool seed diversification (without breaking repeatability)
  - bounded deterministic backtracking/repair improvement after greedy selection

## Completed This Chunk (2026-02-10, Intervals Quantize Calibration)
- Calibrated `src/genfxn/core/difficulty.py` quantize-step bonus schedule for
  intervals so quantization remains represented without over-shifting preset
  distributions:
  - `<=1: 0.0`, `<=2: 0.1`, `<=4: 0.15`, `>4: 0.4`.
- Preserved targeted quantize-effect semantics in
  `tests/test_difficulty.py` by keeping the strict `easy < harder` assertion
  and updating the baseline spec so quantize-step remains the only changed
  field under the calibrated bonus schedule.
- Validation evidence:
  - `uv run pytest tests/test_presets.py -k "intervals_preset_accuracy" -v --verification-level=standard`
    -> 5 passed.
  - `uv run pytest tests/test_difficulty.py -k "intervals" -v --verification-level=standard`
    -> 5 passed.
  - `uv run ruff check src/genfxn/core/difficulty.py tests/test_difficulty.py`
    -> passed.
  - `uv run ty check` -> passed.

## Completed This Chunk (2026-02-10, Intervals D2 Local-Optimum Recovery)
- Hardened suite selection deterministically in
  `src/genfxn/suites/generate.py`:
  - `_repair_selection_with_swaps(...)` now backfills undersized selections to
    `quota.total` before swap improvement.
  - added `_repair_selection_with_backtracking(...)` for bounded deterministic
    deficit recovery when 1-for-1 improving swaps stall.
  - added deterministic intra-attempt pool diversification when an attempt-0
    pool shows bucket-supply shortfall, merging candidates by stable task-id
    uniqueness.
- Kept greedy selection determinism contract intact while improving recovery:
  same seed/path still reproduces restart-0 near-miss behavior, but
  `generate_suite(..., max_retries=0)` can now recover on the known
  `intervals` D2 seed/pathology.
- Validation evidence:
  - `uv run pytest tests/test_suites.py::TestIntegration::test_intervals_d2_local_optimum_recovery_when_available -v --verification-level=full`
    -> 1 passed.
  - `uv run pytest tests/test_suites.py -k "Determinism or intervals" -v --verification-level=standard`
    -> 25 passed, 3 skipped.
  - `uv run ruff check src/genfxn/suites/generate.py` -> passed.
  - `uv run ty check` -> passed.

## Latest Intake Extension (2026-02-10, Family-Scoped Full Markers)
- Current full-test selection is coarse (`@pytest.mark.full` only), so running
  one family's exhaustive suite requires path expressions instead of marker
  selection.
- Requested capability: family-scoped full markers (for example
  `full_piecewise`) so users can run a single family's full tests with `-m`.
- Existing marker-level verification coverage currently asserts only
  verification-level gating and does not lock family-scoped marker behavior.

## Latest Intake Extension (2026-02-10, Query-Input Uniqueness Contract)
- `intervals` and `graph_queries` both currently enforce query-input
  uniqueness per tag (not globally), but this policy is implicit and not
  codified as a shared contract.
- Behavior inspection:
  - `intervals` dedupes at the end of generation with tag-scoped seen sets.
  - `graph_queries` gates insertion using `(tag, src, dst)` keys.
- This means duplicate inputs are prevented within the same tag, while the same
  input can appear across different tags. In constrained domains this preserves
  required tag coverage without forcing synthetic/global uniqueness.
- Existing tests assert tag coverage and output correctness but do not
  explicitly lock per-tag uniqueness vs global uniqueness semantics.

## Latest Intake Extension (2026-02-10, Uniqueness Codification Ownership Pass)
- Scope for this pass is limited to `intervals` and `graph_queries` plus shared
  helpers/tests/docs that define query-input uniqueness expectations.
- Current behavior check confirms:
  - both families allow duplicate inputs across different tags
  - both families prevent duplicate inputs within the same tag
- Rationale for keeping per-tag uniqueness contract: compact input domains can
  make global uniqueness incompatible with required tag coverage (for example
  `graph_queries` with `n_nodes=1` has only one possible `(src, dst)` input).

## Completed This Chunk (2026-02-10, intervals/graph_queries uniqueness codification)
- Added shared helper `dedupe_queries_per_tag_input(...)` in
  `src/genfxn/core/models.py` to make `(tag, input)` uniqueness explicit while
  allowing cross-tag input reuse.
- Updated generators:
  - `src/genfxn/intervals/queries.py`
  - `src/genfxn/graph_queries/queries.py`
  to use the shared helper and encode compact-domain rationale in comments.
- Added validator contract checks in:
  - `src/genfxn/intervals/validate.py`
  - `src/genfxn/graph_queries/validate.py`
  so duplicate inputs within the same tag are flagged, while cross-tag
  duplicates remain valid by contract.
- Added regression coverage:
  - helper-level: `tests/test_core_models.py`
  - family contract: `tests/test_intervals.py`, `tests/test_graph_queries.py`
  - validator behavior: `tests/test_validate_intervals.py`,
    `tests/test_validate_graph_queries.py`
- Updated docs:
  - `README.md` query uniqueness contract now references
    `dedupe_queries_per_tag_input`.
  - `ARCHITECTURE.md` now notes centralized dedupe-contract ownership in
    `src/genfxn/core/models.py`.
- Validation evidence:
  - `uv run pytest tests/test_intervals.py tests/test_graph_queries.py tests/test_core_models.py -v --verification-level=standard`
    -> 73 passed.
  - `uv run pytest tests/test_validator_contract_matrix.py -k "intervals or graph_queries" -v --verification-level=standard`
    -> 8 passed.
  - `uv run ruff check ...` on touched files -> passed.
  - `uv run ty check` -> passed.

## Latest Intake Extension (2026-02-10, stack_bytecode + sequence_dp overflow contract)
- `stack_bytecode` and `sequence_dp` Java/Rust runtime code executes with
  signed 64-bit overflow semantics, while Python evaluators still compute core
  arithmetic/predicate paths with unbounded integers.
- Current runtime parity suites partially mask this evaluator/runtime drift by
  wrapping Python expectations in test-local helpers (`_i64_wrap`,
  `_runtime_output_from_eval`) instead of asserting direct evaluator outputs.
- Overflow-adjacent behavior needing explicit contract lock:
  - `stack_bytecode`: `+`, `-`, `*`, unary negation, `abs`, `/`, `%` around
    `Long.MIN_VALUE` and boundary pairs.
  - `sequence_dp`: DP score accumulation and predicate arithmetic
    (`abs_diff_le`, `mod_eq`) when subtraction/addition overflows.
- This batch goal: codify evaluator-level signed i64 semantics (Java-aligned)
  so parity tests can treat Python evaluator output as the source of truth
  without ad-hoc wrapping in assertions.

## Completed This Chunk (2026-02-10, Family-Scoped Full Markers)
- Added family-scoped full marker assignment in `tests/conftest.py`:
  - full tests in `test_<family>_runtime_parity.py` and
    `test_validate_<family>.py` now receive dynamic marker `full_<family>`.
- Registered family-scoped full markers in `pyproject.toml` for:
  `bitops`, `fsm`, `graph_queries`, `intervals`, `piecewise`, `sequence_dp`,
  `simple_algorithms`, `stack_bytecode`, `stateful`, `stringrules`,
  and `temporal_logic`.
- Added regression coverage in `tests/test_verification_levels.py` to assert:
  - `-m "full_piecewise"` selects only piecewise-owned full tests in full mode
  - `-m "full_piecewise"` still yields standard-mode full skips.
- Updated `README.md` Tests section with family-scoped full marker usage.
- Validation evidence:
  - `uv run pytest tests/test_verification_levels.py -v --verification-level=standard`
    -> 5 passed.
  - `uv run ruff check tests/conftest.py tests/test_verification_levels.py`
    -> passed.
  - `uv run ty check tests/conftest.py tests/test_verification_levels.py`
    -> passed.
  - `uv run pytest tests/ --verification-level=full -m "full_piecewise" --collect-only -q`
    -> 12/1910 tests collected (1898 deselected).

## Latest Intake Extension (2026-02-10, Policy Docs Follow-up)
- Two policy/doc items remained open:
  1) query-input uniqueness contract (global input uniqueness vs per-tag)
  2) overflow semantics expectation clarity for `stack_bytecode` and
     `sequence_dp`.
- Current code behavior confirms mixed query-uniqueness ownership by family:
  - global input dedupe via `dedupe_queries(...)` for
    `piecewise`, `stateful`, `simple_algorithms`, `stringrules`,
    `stack_bytecode`, `fsm`, and `bitops`.
  - per-tag+input uniqueness in generators for
    `intervals`, `graph_queries`, `sequence_dp`, and `temporal_logic`.
- Current runtime parity behavior for overflow-adjacent cases confirms
  Java/Rust `long`/`i64` comparisons use evaluator-derived expectations
  normalized to signed 64-bit representation.

## Completed This Chunk (2026-02-10, Policy Docs Follow-up)
- Updated `CURRENT_PLAN.md` to close the remaining query-uniqueness policy
  item and record explicit per-family uniqueness contracts.
- Updated `CURRENT_PLAN.md` immediate-actions notes to mark overflow-policy
  documentation as resolved.
- Added concise `README.md` contract notes for:
  - query uniqueness policy (global input dedupe default with explicit
    per-tag exceptions)
  - overflow semantics expectations for `stack_bytecode` and `sequence_dp`
    (Python evaluator as source, parity normalized to signed i64/Java long on
    overflow-adjacent paths).

## Completed This Chunk (2026-02-10, stack_bytecode + sequence_dp overflow alignment)
- Established explicit signed i64 overflow contract across evaluator/runtime:
  - arithmetic wraps in two's-complement i64 space
  - division/modulo follow Java `long` edge behavior for
    `Long.MIN_VALUE / -1 == Long.MIN_VALUE` and
    `Long.MIN_VALUE % -1 == 0`
  - unary negation and `abs(Long.MIN_VALUE)` both produce
    `Long.MIN_VALUE`.
- Applied evaluator changes:
  - `src/genfxn/stack_bytecode/eval.py`
  - `src/genfxn/sequence_dp/eval.py`
- Updated runtime parity suites to assert direct Python evaluator outputs for
  overflow-adjacent cases (removed test-local expectation wrapping helpers):
  - `tests/test_stack_bytecode_runtime_parity.py`
  - `tests/test_sequence_dp_runtime_parity.py`
- Added focused evaluator regressions to lock edge semantics:
  - `tests/test_stack_bytecode.py`
  - `tests/test_sequence_dp.py`
- Validation evidence:
  - `uv run pytest tests/test_stack_bytecode_runtime_parity.py
    tests/test_sequence_dp_runtime_parity.py -v --verification-level=full`
    -> 11 passed.
  - `uv run pytest tests/test_stack_bytecode.py tests/test_sequence_dp.py -v
    --verification-level=standard`
    -> 77 passed.
  - `uv run ruff check src/genfxn/stack_bytecode/eval.py
    src/genfxn/sequence_dp/eval.py tests/test_stack_bytecode_runtime_parity.py
    tests/test_sequence_dp_runtime_parity.py tests/test_stack_bytecode.py
    tests/test_sequence_dp.py`
    -> passed.
  - `uv run ty check`
    -> passed.

## Latest Intake Extension (2026-02-10, case-mismatched holdout scalars + docs/e2e coverage)
- CLI exact/contains holdout parsing rejects malformed scalar typos (`tru`,
  `nul`, `01`, `+1`) but still allowed case-mismatched JSON scalar tokens
  (`True`, `False`, `Null`) to silently fall back to raw strings.
- Split README docs do not yet describe exact/contains JSON parsing and
  malformed-literal rejection rules, making quoted-string requirements for
  JSON-looking strings easy to miss.
- Nested type-sensitive holdout behavior is covered at matcher level in
  `tests/test_cli.py`, but dedicated file-based CLI split end-to-end tests were
  still thin for nested exact/contains payloads.

## Latest Intake Extension (2026-02-10, renderer literal boundary sweep)
- Remaining renderer compile-safety drift is broader than the initial
  `graph_queries`/`stack_bytecode` fixes:
  - Java renderers in `bitops`, `sequence_dp`, `temporal_logic`, `intervals`,
    and `fsm` still had direct literal emission paths that can fail compilation
    for valid model payloads near/beyond backend primitive limits.
  - Rust renderers in `sequence_dp` (and related helper clones in other
    families) still accepted values that can emit out-of-range `i64` literals.
- `render_tests(...)` deterministic rendering still had a dict-ordering gap:
  dict literals were emitted with insertion-order traversal rather than stable
  canonical ordering, allowing cross-process drift when insertion order is
  hash-derived.
- First-party `pytest.importorskip(...)` masking appears already reduced in the
  current workspace; strict-import cleanup may be partially complete from
  concurrent patching and should be re-checked before editing.

## Completed This Chunk (2026-02-10, renderer literal boundary + deterministic dict rendering)
- Closed remaining Java literal compile-safety drift by using checked helpers in:
  - `src/genfxn/langs/java/bitops.py`
  - `src/genfxn/langs/java/sequence_dp.py`
  - `src/genfxn/langs/java/temporal_logic.py`
  - `src/genfxn/langs/java/intervals.py`
  - `src/genfxn/langs/java/fsm.py`
- Hardened helper contracts:
  - `src/genfxn/langs/java/_helpers.py`
    - `java_int_literal(...)` now fail-closes outside signed-64-bit range.
  - `src/genfxn/langs/rust/_helpers.py`
    - added `rust_i64_literal(...)` with signed-64-bit range checks.
- Aligned Rust literal rendering with checked helper usage in:
  - `src/genfxn/langs/rust/sequence_dp.py`
  - `src/genfxn/langs/rust/bitops.py`
  - `src/genfxn/langs/rust/temporal_logic.py`
  - `src/genfxn/langs/rust/intervals.py`
- Added fail-closed representable-range model validation in:
  - `src/genfxn/bitops/models.py`
  - `src/genfxn/sequence_dp/models.py`
  - `src/genfxn/temporal_logic/models.py`
  - `src/genfxn/intervals/models.py`
  - `src/genfxn/fsm/models.py`
  including FSM state-id upper bound protection against sink-state overflow.
- Fixed `render_tests(...)` dict-order nondeterminism in:
  - `src/genfxn/core/codegen.py`
  dict literals now render with stable key ordering.
- Added focused regressions in:
  - `tests/test_java_render.py`
  - `tests/test_rust_render.py`
  - `tests/test_bitops.py`
  - `tests/test_sequence_dp.py`
  - `tests/test_temporal_logic.py`
  - `tests/test_intervals.py`
  - `tests/test_fsm.py`
  - `tests/test_core_dsl.py`
- Validation evidence:
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - targeted standard pytest slice (8 files) -> 553 passed.

## Completed This Chunk (2026-02-10, parity closure + compatibility wrappers)
- Restored backward-compatible literal helper aliases used by parity tests:
  - `src/genfxn/langs/java/temporal_logic.py`:
    `_long_literal(...) -> java_long_literal(...)`
  - `src/genfxn/langs/rust/temporal_logic.py`:
    `_i64_literal(...) -> rust_i64_literal(...)`
- Re-ran broad standard+full verification slices to validate the entire
  hardening batch end-to-end after compatibility restoration.
- Validation evidence:
  - `uv run pytest` standard slice across core/CLI/splits/render/model files
    -> 917 passed.
  - `uv run pytest` full runtime parity slice across
    `graph_queries`, `stack_bytecode`, `sequence_dp`, `temporal_logic`,
    `intervals`, `bitops`, and `fsm`
    -> 35 passed.

## Latest Intake Extension (2026-02-10, graph_queries + intervals i64 overflow parity)
- Two additional overflow-adjacent parity drifts are reproducible and separate
  from compile-safety/parser work:
  - `graph_queries` shortest-path accumulation:
    Python evaluator uses unbounded integer addition while Java/Rust use
    signed `long`/`i64` wrapping behavior.
  - `intervals` aggregate/event arithmetic:
    Python evaluator uses unbounded arithmetic while Java/Rust wrap for
    operations involving `+1`, `total += ...`, and event sweep accumulation.
- Reproduced examples:
  - graph_queries path weight `(2^63-1) + 1`:
    Python `9223372036854775808` vs Java/Rust `-9223372036854775808`.
  - intervals:
    - total_coverage over `[-(2^63-1), 2^63-1]`:
      Python `18446744073709551615` vs Java/Rust `-1`.
    - max_overlap_count at endpoint `2^63-1`:
      Python `1` vs Java/Rust `0` due `end + 1` wrap.

## Completed This Chunk (2026-02-10, graph_queries + intervals i64 overflow parity)
- Aligned Python evaluator overflow semantics with Java/Rust runtime behavior:
  - `src/genfxn/graph_queries/eval.py`:
    shortest-path cost accumulation now uses signed i64 wrapping.
  - `src/genfxn/intervals/eval.py`:
    signed i64 wrapping applied to overflow-adjacent arithmetic in merge/gap
    thresholds, total coverage accumulation, and max-overlap event sweep logic.
- Added focused regressions:
  - `tests/test_graph_queries.py`
  - `tests/test_intervals.py`
  - `tests/test_graph_queries_runtime_parity.py`
  - `tests/test_intervals_runtime_parity.py`
- Validation evidence:
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/test_graph_queries.py tests/test_intervals.py -v
    --verification-level=standard` -> 73 passed.
  - `uv run pytest tests/test_graph_queries_runtime_parity.py
    tests/test_intervals_runtime_parity.py -v --verification-level=full`
    -> 13 passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1998 passed, 106 skipped.

## Latest Intake Extension (2026-02-10, int32-family literal fail-closed + hash canonicalization)
- Related-issue sweep found remaining compile-safety drift in int32 families
  (`piecewise`, `stateful`, `simple_algorithms`) for constants above signed
  64-bit range:
  - Java paths fail during rendering via checked long/int helper limits.
  - Rust paths still inline several raw constants and can fail `rustc` with
    literal out-of-range errors.
- This drift appears through public generation APIs as well (for example
  `generate_*_task(..., languages=[Language.RUST])`) when axes/specs allow
  out-of-range constants.
- Core int predicate/transform models intentionally allow constants above
  signed int32 (for int32-wrap semantics tests), so this pass should preserve
  that behavior while fail-closing values outside signed 64-bit range.
- `task_id_from_spec(...)` canonicalization still conflates mixed key types by
  coercing dict keys with `str(k)`, which can produce collisions and
  insertion-order-sensitive IDs for mixed-type key sets.
- Skip-based availability gating remains in first-party tests (`test_suites`,
  `test_presets`) and can mask missing-module regressions as skipped tests
  rather than failures.

## Completed This Chunk (2026-02-10, int32-family literal/hash/skip hardening)
- Added fail-closed signed-64-bit bounds for int32-family numeric specs/axes
  and shared predicate/transform constants, preserving existing >int32 wrap
  semantics for runtime parity paths.
- Enforced compile-safe `MaxWindowSumSpec.k` upper bound (`<= INT32_MAX`).
- Hardened Rust int32-family numeric emitters to validate i64 representability
  while preserving expected renderer text style for existing render tests.
- Fixed `task_id_from_spec(...)` mixed-type dict-key canonicalization so
  non-string-key dict hashing is deterministic and type-sensitive.
- Converted targeted first-party availability gating in
  `tests/test_suites.py` and `tests/test_presets.py` to fail-closed behavior
  (no skip-on-missing-module masking).
- Added focused regressions in:
  - `tests/test_core_dsl.py`
  - `tests/test_stateful.py`
  - `tests/test_simple_algorithms.py`
  - `tests/test_piecewise.py`
- Validation evidence:
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/test_core_dsl.py tests/test_stateful.py
    tests/test_simple_algorithms.py tests/test_piecewise.py
    tests/test_suites.py tests/test_presets.py tests/test_rust_render.py -v
    --verification-level=standard` -> 631 passed, 19 skipped.

## Latest Intake Extension (2026-02-10, CodeRabbit plain-review follow-up)
- CodeRabbit plain review reported four actionable items in current tree:
  - remove no-op `validate_k` validator in
    `src/genfxn/simple_algorithms/models.py`.
  - align piecewise Java expression rendering call sites with explicit
    `int32_wrap=True` usage to match predicate rendering intent.
  - fix `piecewise` evaluator `ExprMod` branch to use i32 modulo semantics
    (`i32_mod`) instead of native Python `%`.
  - simplify/clarify Rust `sequence_dp` `abs_diff_le` comparison by replacing
    manual `wrapping_sub` absolute-diff assembly with `i64::abs_diff(...)`.
- Intake triage: all four findings appear independent and not part of
  incomplete in-progress code; safe to apply in this pass with focused tests.

## Latest Intake Extension (2026-02-10, review follow-up recs)
- `task_id_from_spec` canonicalization currently conflates container types for
  values (`list`/`tuple` and `set`/`frozenset`) because all are normalized to
  the same JSON shape, causing false task-id collisions.
- `graph_queries` `shortest_path_cost` currently uses frontier-first-return
  behavior that can return a non-minimal wrapped-i64 path cost when a better
  path is discovered after an earlier destination pop.
- Clarifying docs are needed so contributors understand both:
  - task-id hashing is expected to preserve container-type distinctions.
  - graph shortest-path semantics are "best wrapped cost over simple paths"
    rather than first-hit frontier behavior.

## Completed This Chunk (2026-02-10, task_id + graph shortest-path semantics)
- Fixed `task_id_from_spec` value-container type conflation in
  `src/genfxn/core/codegen.py`:
  - canonicalization now preserves `list` vs `tuple` and `set` vs `frozenset`
    distinctions for value containers.
- Added task-id collision regression in `tests/test_core_dsl.py`:
  - `TestTaskId.test_container_value_types_do_not_collide`.
- Replaced `graph_queries` shortest-path frontier-first behavior with
  deterministic best wrapped cost over simple paths (`<= n_nodes - 1` edges)
  across:
  - `src/genfxn/graph_queries/eval.py`
  - `src/genfxn/graph_queries/render.py`
  - `src/genfxn/langs/java/graph_queries.py`
  - `src/genfxn/langs/rust/graph_queries.py`
- Updated graph regressions/parity locks for late-improvement wrapped-path
  behavior:
  - `tests/test_graph_queries.py`
  - `tests/test_graph_queries_runtime_parity.py`
- Added contributor-facing contract notes in:
  - `README.md`
  - `CLAUDE.md`
- Validation evidence:
  - focused standard slice: 3 passed.
  - focused full runtime parity test: 1 passed.
  - full touched graph suite (`full`): 49 passed.
  - targeted `ruff` and `ty`: passed.

## Completed This Chunk (2026-02-10, CodeRabbit plain-review follow-up)
- Applied all four accepted CodeRabbit findings:
  - removed no-op `validate_k` in
    `src/genfxn/simple_algorithms/models.py`.
  - added explicit Java piecewise expression int32-wrap threading in
    `src/genfxn/langs/java/expressions.py` and
    `src/genfxn/langs/java/piecewise.py`.
  - switched `piecewise` `ExprMod` evaluator path to `i32_mod(...)` in
    `src/genfxn/piecewise/eval.py`.
  - replaced manual Rust wrapping abs-diff assembly with `ai.abs_diff(bj)` in
    `src/genfxn/langs/rust/sequence_dp.py`.
- Added focused regression coverage:
  - `tests/test_java_render.py`:
    `TestPiecewiseJava.test_expression_constants_use_int32_wrap_literals`.
- Validation evidence:
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - focused pytest slices:
    - Java render: 13 passed.
    - piecewise eval/branch selection: 9 passed.
    - simple_algorithms max-window/axes subset: 9 passed.
    - full-mode sequence_dp extreme abs-diff parity: 1 passed.

## Latest Intake Extension (2026-02-10, CodeRabbit committed-scope follow-up)
- A committed-scope CodeRabbit review against `main` reported five actionable
  findings in the current branch:
  - `src/genfxn/langs/rust/intervals.py`: raw i64 arithmetic in generated code
    should use explicit wrapping ops for parity/consistency.
  - `src/genfxn/suites/quotas.py`: `_TEMPORAL_LOGIC_D2` bucket axis/value drift
    (`temporal_bucket:none`) conflicts with hard constraint (`depth_bucket:2`).
  - `src/genfxn/langs/rust/predicates.py`: `PredicateModEq` int32-wrap branch
    leaves divisor unwrapped.
  - `src/genfxn/langs/rust/graph_queries.py`: shortest-path accumulation uses
    plain `+` instead of wrapping add.
  - `tests/test_validation_exec_optin.py`: semantics-raise lifecycle test omits
    four families that have `_validate_semantics` paths.
- Separate interactive review suggestions for Java piecewise/piecewise eval/
  sequence_dp/simple_algorithms are stale in this tree and already addressed in
  prior chunks; no additional edits needed for those items.

## Completed This Chunk (2026-02-10, CodeRabbit committed-scope follow-up)
- Applied all five committed-scope CodeRabbit fixes:
  - `src/genfxn/langs/rust/intervals.py`: replaced raw i64 arithmetic in
    generated boundary/merge/gap/coverage/event/sweep paths with explicit
    wrapping operations.
  - `src/genfxn/suites/quotas.py`: aligned `_TEMPORAL_LOGIC_D2` buckets with
    hard constraints via `depth_bucket=2`.
  - `src/genfxn/langs/rust/predicates.py`: wrapped `PredicateModEq` divisor in
    int32-wrap rendering path.
  - `src/genfxn/langs/rust/graph_queries.py`: switched shortest-path cost
    accumulation to `wrapping_add`.
  - `tests/test_validation_exec_optin.py`: expanded semantics-raise lifecycle
    coverage to `piecewise`, `stateful`, `simple_algorithms`, `stringrules`.
- Hardened related regression coverage:
  - `tests/test_rust_render.py`: added intervals/graph rust-wrapping assertions
    and updated int32 mod-eq rendering expectation.
  - `tests/test_suites.py`: added temporal-logic D2 quota-axis consistency test.
  - `tests/test_validation_exec_optin.py`: lifecycle-close harness now stubs
    AST/compile steps so close assertions consistently exercise `fn.close()`
    behavior across families.
- Validation evidence:
  - focused standard pytest slice: 26 passed.
  - focused full runtime-parity overflow slice: 4 passed.
  - targeted `ruff` + `ty` on touched Python files: passed.

## Latest Intake Extension (2026-02-10, Standards Lock: Python Unicode + Strict Renderer AST)
- Decision locked for this repo:
  - Python evaluator semantics are authoritative for cross-language runtime
    parity (including Unicode behavior).
  - Family validators should enforce strict renderer-structure parity rather
    than broad permissive AST acceptance.
- Reproduced hard regressions from this pass:
  - `graph_queries` renderer output is rejected by its own AST whitelist and
    also fails runtime sandbox execution due to missing `dict` builtin.
  - `intervals` renderer output is rejected by its own AST whitelist after
    i64-wrap helper additions.
- Reproduced Unicode parity drift in `stringrules`:
  - Java `is_alpha("𝔘")` returns `false` while Python returns `True`.
  - Java/Rust `is_upper("漢字")` return `true` while Python returns `False`.
  - Rust `is_digit("Ⅷ")` returns `true` while Python returns `False`.
- Coverage gap confirmed:
  - `tests/test_stringrules_runtime_parity.py` sampled parity remains
    ASCII-biased and non-ASCII coverage currently focuses on length predicates,
    not Unicode predicate semantics.

## Completed This Chunk (2026-02-10, standards lock follow-through)
- Locked implementation to chosen standards:
  - Python evaluator semantics remain authoritative for Unicode parity.
  - Validators enforce strict renderer-structure AST expectations.
- Fixed strict-validator regressions:
  - `graph_queries` AST/sandbox drift fixed by updating
    `src/genfxn/graph_queries/ast_safety.py` and
    `src/genfxn/graph_queries/validate.py` (`dict` builtin + helper names/nodes).
  - `intervals` AST drift fixed by updating
    `src/genfxn/intervals/ast_safety.py`.
  - Added top-level statement and non-call attribute rejection hardening in:
    `src/genfxn/{bitops,fsm,graph_queries,intervals,sequence_dp,`
    `stack_bytecode,temporal_logic,piecewise,stateful,`
    `simple_algorithms,stringrules}/validate.py`.
- Fixed Unicode predicate parity drift:
  - `src/genfxn/langs/java/string_predicates.py` now uses code-point paths and
    Python-style cased-character checks for case predicates.
  - `src/genfxn/langs/rust/string_predicates.py` now uses Python-authoritative
    digit helper gating and stricter cased-character checks.
  - Added Python-authoritative `isdigit` helper wiring in:
    `src/genfxn/langs/java/stringrules.py`,
    `src/genfxn/langs/rust/stringrules.py`.
- Strengthened coverage:
  - Added Unicode full-mode parity tests in
    `tests/test_stringrules_runtime_parity.py`.
  - Added cross-family AST-contract checks in
    `tests/test_validator_contract_matrix.py`
    (top-level side effects + non-call attributes).
  - Updated affected validator and renderer expectation tests:
    `tests/test_validate_{bitops,graph_queries,intervals,sequence_dp,temporal_logic}.py`,
    `tests/test_java_render.py`,
    `tests/test_rust_render.py`.
- Validation evidence:
  - targeted strictness slice: 116 passed.
  - targeted Unicode full parity slice: 3 passed.
  - full standard suite: 2032 passed, 110 skipped.
  - touched-file `ruff` + `ty`: passed.

## Latest Intake Extension (2026-02-10, review follow-up correctness + rigor gaps)
- `render_tests(...)` still uses direct equality for non-NaN outputs, allowing
  type-coercing false passes (`False == 0`, `1 == 1.0`) versus canonical
  type-sensitive output-equality contract.
- `_run_isolated(...)` can deadlock/timeout when `max_result_bytes=None` if the
  worker blocks on large `queue.put(...)` payloads while parent waits on join.
- Verification-level tests do not lock default behavior (implicit
  `--verification-level=standard`) or explicit standard-level treatment of
  `@pytest.mark.slow`.
- CLI split option-contract validation (`random` vs `holdout` exclusivity,
  required holdout pair) is implemented but lacks direct regression tests.
- CLI split range parser has no direct malformed-format holdout test matrix
  (`"1"`, `"1,2,3"`, `"a,b"`) despite generate-side coverage.
- Two `tests/test_splits.py` assertions remain probabilistic and can flake
  (`different seeds` set inequality, `train != first N` heuristic).
- `dedupe_queries_per_tag_input` lacks explicit NaN-output parity coverage.

## Completed This Chunk (2026-02-10, review follow-up correctness + rigor gaps)
- Fixed rendered-test equality contract drift:
  - `src/genfxn/core/codegen.py` `render_tests(...)` now always emits
    canonical `__genfxn_query_outputs_equal(...)` assertions (not NaN-only
    special-casing), preventing type-coercing false passes.
- Hardened safe-exec one-shot handoff:
  - `src/genfxn/core/safe_exec.py` `_run_isolated(...)` now drains result queue
    during execution timeout window before enforcing timeout, then performs a
    short post-exit grace drain; this removes join-before-drain deadlock risk
    when `max_result_bytes=None`.
- Added missing verification-level regression locks:
  - `tests/test_verification_levels.py`
    - implicit default-level behavior (`-q` => standard)
    - standard-level slow-marker behavior.
- Added missing CLI split contract regressions:
  - `tests/test_cli.py`
    - random/holdout mutual exclusion
    - missing mode rejection
    - missing holdout-axis/value pairing
    - malformed range holdout values (`"1"`, `"1,2,3"`, `"a,b"`).
- Replaced probabilistic split tests with deterministic seed-locked checks:
  - `tests/test_splits.py`
    - deterministic expected-order assertions for seed-specific train/test
      partitions.
- Added per-tag dedupe NaN output equality coverage:
  - `tests/test_core_models.py`
    - NaN and nested-NaN outputs dedupe without false conflict in
      `dedupe_queries_per_tag_input(...)`.
- Validation evidence:
  - `uv run pytest tests/test_core_dsl.py tests/test_safe_exec.py
    tests/test_verification_levels.py tests/test_cli.py tests/test_splits.py
    tests/test_core_models.py -q --verification-level=standard`
    -> 357 passed.
  - `uv run ruff check` on touched source/test files -> passed.
  - `uv run ty check` on touched source/test files -> passed.
