# Goal: Synthetic Function Dataset Generator

Build a library for generating synthetic datasets to evaluate ML models on function learning tasks. Given input/output examples, can a model predict outputs or reconstruct the underlying code?

## Design Principles

- **Programmatic**: Fully deterministic, no LLM in the loop, reproducible via seed
- **Axis-labeled**: Explicit difficulty knobs for systematic variation and controlled generalization studies
- **Coverage-aware**: Queries guarantee every branch/rule/mode gets exercised
- **Dual-use**: Supports both "predict the output" and "reconstruct code from tests" task formulations

## Four Generator Families

### 1. Piecewise Numeric Functions
`f(x: int) -> int`

Threshold-based branching with varying expression complexity.

**Key axes**: n_branches, expression types (affine/quadratic/abs/mod), threshold gaps, comparator patterns

**Tests**: Can models learn branching logic and mathematical expressions?

### 2. String Rules Transducer
`f(s: str) -> str`

Ordered pattern/class matching rules that transform strings (like a mini regex state machine).

**Key axes**: n_rules, pattern vs class rule mix, overlap level (precedence conflicts), default action

**Tests**: Can models learn ordered rule application and handle precedence?

### 3. Stateful Iteration
`f(xs: list[int]) -> int`

Accumulator patterns that track state across a sequence.

**Templates**:
- Conditional linear sum (predicate-gated accumulator updates)
- Resetting best prefix sum (Kadane-style with reset triggers)
- Longest run (track run length matching a predicate)

**Key axes**: predicate type, transform type, value range, coefficient scale

**Tests**: Can models learn update rules and state invariants?

### 4. Simple Algorithms
`f(xs: list[int]) -> int`

Algorithms where intent compresses well but correctness depends on subtle details.

**Templates**:
- Most frequent (tie-break: smallest vs first-seen)
- Count pairs sum (all index pairs vs unique value pairs)
- Max window sum (edge cases for invalid k)

**Key axes**: tie-break semantics, counting mode, window size

**Tests**: Can models handle edge cases and subtle semantic distinctions?

## Output Schema

Each generated task produces:

```python
Task = {
    "task_id": str,           # hash of spec for deduping
    "family": str,            # which generator
    "axes": dict,             # the knobs sampled (for split analysis)
    "spec": dict,             # canonical rule representation
    "code": str,              # ground-truth Python function
    "queries": list,          # inputs
    "outputs": list,          # ground-truth outputs
    "query_tags": list,       # "coverage" | "boundary" | "typical" | "adversarial"
    "tests_py": str,          # Python asserts for reconstruction round
}
```

## Key Use Cases

1. **Controlled generalization studies**: Hold out specific axes (e.g., "never train on high-overlap string rules") for clean analysis of *why* models fail
2. **Difficulty curve analysis**: Axis labels enable systematic difficulty comparisons
3. **Dual evaluation**: Same tasks support output prediction and code reconstruction

---

## Current Scope: MVP

### Families to Implement First

**Family 1 (Piecewise Numeric)** + **Family 3 (Stateful Iteration)**

Rationale:
- Different input types: `int -> int` vs `list[int] -> int` (scalar vs sequence)
- Different logic patterns: branching vs accumulation/state tracking
- Family 3's predicate/transform DSL is shared infrastructure that Family 4 will reuse
- Families 2 and 4 can be added later without architectural changes

### Axis Types to Exercise

One representative of each "flavor" to validate the split builder:

1. **Categorical**: `template` - holdout by category
2. **Discrete numeric**: `n_branches` - holdout by value or bin
3. **Nested/compound**: `expr_types` (list of allowed types) - complex axis structures
4. **Range-based**: `value_range` - holdout by range characteristics

### MVP Deliverables

1. Generator infrastructure supporting both families
2. Spec → eval → queries → render pipeline for each
3. Axis-heldout split builder
4. JSONL output with task schema

### Deferred (Families 2 & 4)

- **String Rules Transducer**: Different I/O type (str), scanning semantics
- **Simple Algorithms**: Reuses Family 3's predicate DSL, adds edge-case-heavy templates
