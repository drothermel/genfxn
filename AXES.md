# Axes Reference

This document describes all configurable axes for task generation and dataset splitting.

**Sampling Axes** control what gets generated (configured via `*Axes` classes or CLI flags).
**Spec Field Paths** identify fields in generated specs for holdout splits.

---

## Piecewise

Conditional functions with predicate-guarded branches: `f(x: int) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `n_branches` | int (1-5) | 2 | `--n-branches` | Number of conditional branches |
| `expr_types` | list | `[affine]` | `--expr-types` | Expression types to sample from |
| `value_range` | (lo, hi) | (-100, 100) | `--value-range` | Range for input values in queries |
| `coeff_range` | (lo, hi) | (-5, 5) | `--coeff-range` | Range for expression coefficients |
| `threshold_range` | (lo, hi) | (-50, 50) | `--threshold-range` | Range for predicate thresholds |
| `divisor_range` | (lo, hi) | (2, 10) | `--divisor-range` | Range for mod divisors |

### Expression Types

| Value | CLI | Description |
|-------|-----|-------------|
| `AFFINE` | `affine` | `a*x + b` |
| `QUADRATIC` | `quadratic` | `a*x^2 + b*x + c` |
| `ABS` | `abs` | `abs(a*x + b)` |
| `MOD` | `mod` | `(a*x + b) % m` |

### Predicate Types (for branch conditions)

| Value | CLI | Description |
|-------|-----|-------------|
| `EVEN` | `even` | `x % 2 == 0` |
| `ODD` | `odd` | `x % 2 != 0` |
| `LT` | `lt` | `x < threshold` |
| `LE` | `le` | `x <= threshold` |
| `GT` | `gt` | `x > threshold` |
| `GE` | `ge` | `x >= threshold` |
| `MOD_EQ` | `mod_eq` | `x % divisor == remainder` |
| `IN_SET` | `in_set` | `x in {values}` |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `default_expr.kind` | `affine`, `quadratic`, `abs`, `mod` | Default branch expression |
| `branches.N.expr.kind` | same | Expression in branch N |
| `branches.N.condition.kind` | predicate types | Condition type in branch N |

---

## Stateful

Iteration functions with accumulator state: `f(xs: list[int]) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `templates` | list | all | `--templates` | Template types to sample from |
| `predicate_types` | list | all except `in_set` | `--predicate-types` | Predicate types for conditions |
| `transform_types` | list | all except `clip` | `--transform-types` | Transform types for accumulators |
| `value_range` | (lo, hi) | (-100, 100) | `--value-range` | Range for list element values |
| `list_length_range` | (lo, hi) | (5, 20) | `--list-length-range` | Range for test list lengths |
| `threshold_range` | (lo, hi) | (-50, 50) | `--threshold-range` | Range for predicate thresholds |
| `divisor_range` | (lo, hi) | (2, 10) | `--divisor-range` | Range for mod divisors |
| `shift_range` | (lo, hi) | (-10, 10) | `--shift-range` | Range for shift transform values |
| `scale_range` | (lo, hi) | (-5, 5) | `--scale-range` | Range for scale transform factors |

### Template Types

| Value | CLI | Description |
|-------|-----|-------------|
| `CONDITIONAL_LINEAR_SUM` | `conditional_linear_sum` | Accumulates with predicate-based transforms |
| `RESETTING_BEST_PREFIX_SUM` | `resetting_best_prefix_sum` | Tracks best sum with reset conditions |
| `LONGEST_RUN` | `longest_run` | Counts longest consecutive matching run |

**Difficulty ranking**: `longest_run` < `conditional_linear_sum` < `resetting_best_prefix_sum`

### Predicate Types

| Value | CLI | Description |
|-------|-----|-------------|
| `EVEN` | `even` | `x % 2 == 0` |
| `ODD` | `odd` | `x % 2 != 0` |
| `LT` | `lt` | `x < threshold` |
| `LE` | `le` | `x <= threshold` |
| `GT` | `gt` | `x > threshold` |
| `GE` | `ge` | `x >= threshold` |
| `MOD_EQ` | `mod_eq` | `x % divisor == remainder` |

### Transform Types

| Value | CLI | Description |
|-------|-----|-------------|
| `IDENTITY` | `identity` | `x` (no change) |
| `ABS` | `abs` | `abs(x)` |
| `SHIFT` | `shift` | `x + k` |
| `NEGATE` | `negate` | `-x` |
| `SCALE` | `scale` | `x * k` |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `template` | template types | Which algorithm template |
| `predicate.kind` | predicate types | Condition predicate |
| `true_transform.kind` | transform types | Transform when predicate is true |
| `false_transform.kind` | transform types | Transform when predicate is false |
| `reset_predicate.kind` | predicate types | Reset condition (resetting_best_prefix_sum) |
| `match_predicate.kind` | predicate types | Match condition (longest_run) |

---

## Simple Algorithms

Algorithms with subtle edge cases: `f(xs: list[int]) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `templates` | list | all | `--algorithm-types` | Algorithm templates to sample |
| `tie_break_modes` | list | all | `--tie-break-modes` | Tie-break semantics |
| `counting_modes` | list | all | `--counting-modes` | Pair counting modes |
| `value_range` | (lo, hi) | (-100, 100) | `--value-range` | Range for list element values |
| `list_length_range` | (lo, hi) | (5, 20) | `--list-length-range` | Range for test list lengths |
| `target_range` | (lo, hi) | (-50, 50) | `--target-range` | Range for target sum |
| `window_size_range` | (lo, hi) | (1, 10) | `--window-size-range` | Range for window size k |
| `empty_default_range` | (lo, hi) | (0, 0) | — | Range for empty/invalid defaults |

### Template Types

| Value | CLI | Description |
|-------|-----|-------------|
| `MOST_FREQUENT` | `most_frequent` | Find most common element |
| `COUNT_PAIRS_SUM` | `count_pairs_sum` | Count pairs summing to target |
| `MAX_WINDOW_SUM` | `max_window_sum` | Maximum sum of k consecutive elements |

### Tie-Break Modes (most_frequent)

| Value | CLI | Description |
|-------|-----|-------------|
| `SMALLEST` | `smallest` | Return smallest value among ties |
| `FIRST_SEEN` | `first_seen` | Return first encountered among ties |

### Counting Modes (count_pairs_sum)

| Value | CLI | Description |
|-------|-----|-------------|
| `ALL_INDICES` | `all_indices` | Count all (i, j) index pairs where i < j |
| `UNIQUE_VALUES` | `unique_values` | Count unique (a, b) value pairs |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `template` | template types | Which algorithm |
| `tie_break` | `smallest`, `first_seen` | Tie-break mode (most_frequent) |
| `counting_mode` | `all_indices`, `unique_values` | Counting mode (count_pairs_sum) |
| `k` | integer | Window size (max_window_sum) |
| `target` | integer | Target sum (count_pairs_sum) |

---

## String Rules

Ordered pattern matching with first-match-wins: `f(s: str) -> str`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `n_rules` | int (1-8) | 3 | `--n-rules` | Number of rules |
| `predicate_types` | list | all | `--string-predicate-types` | String predicate types |
| `transform_types` | list | all | `--string-transform-types` | String transform types |
| `overlap_level` | enum | `low` | `--overlap-level` | How much rules can shadow each other |
| `string_length_range` | (lo, hi) | (1, 20) | `--string-length-range` | Range for input string lengths |
| `charset` | str | `ascii_letters_digits` | — | Character set for sampling |
| `prefix_suffix_length_range` | (lo, hi) | (1, 4) | — | Range for prefix/suffix lengths |
| `substring_length_range` | (lo, hi) | (1, 3) | — | Range for substring lengths |
| `length_threshold_range` | (lo, hi) | (1, 15) | — | Range for length comparisons |

### Overlap Levels

| Value | CLI | Description |
|-------|-----|-------------|
| `NONE` | `none` | Rules have disjoint predicates |
| `LOW` | `low` | Occasional overlap (~20% chance) |
| `HIGH` | `high` | Significant shadowing (~60% chance) |

### String Predicate Types

| Value | CLI | Description |
|-------|-----|-------------|
| `STARTS_WITH` | `starts_with` | `s.startswith(prefix)` |
| `ENDS_WITH` | `ends_with` | `s.endswith(suffix)` |
| `CONTAINS` | `contains` | `substring in s` |
| `IS_ALPHA` | `is_alpha` | `s.isalpha()` |
| `IS_DIGIT` | `is_digit` | `s.isdigit()` |
| `IS_UPPER` | `is_upper` | `s.isupper()` |
| `IS_LOWER` | `is_lower` | `s.islower()` |
| `LENGTH_CMP` | `length_cmp` | `len(s) <op> threshold` |

### String Transform Types

| Value | CLI | Description |
|-------|-----|-------------|
| `IDENTITY` | `identity` | `s` (no change) |
| `LOWERCASE` | `lowercase` | `s.lower()` |
| `UPPERCASE` | `uppercase` | `s.upper()` |
| `CAPITALIZE` | `capitalize` | `s.capitalize()` |
| `SWAPCASE` | `swapcase` | `s.swapcase()` |
| `REVERSE` | `reverse` | `s[::-1]` |
| `REPLACE` | `replace` | `s.replace(old, new)` |
| `STRIP` | `strip` | `s.strip()` or `s.strip(chars)` |
| `PREPEND` | `prepend` | `prefix + s` |
| `APPEND` | `append` | `s + suffix` |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `rules.N.predicate.kind` | predicate types | Predicate type for rule N |
| `rules.N.transform.kind` | transform types | Transform type for rule N |
| `default_transform.kind` | transform types | Default when no rule matches |

---

## Stack Bytecode

Stack-machine programs over integer lists: `f(xs: list[int]) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `target_difficulty` | int (1-5) | `None` | — | Optional target difficulty band for stack templates |
| `value_range` | (lo, hi) | (-50, 50) | `--value-range` | Range used for sampled list values in queries |
| `list_length_range` | (lo, hi) | (0, 8) | `--list-length-range` | Range for sampled input lengths |
| `const_range` | (lo, hi) | (-10, 10) | — | Range for sampled constants in instructions |
| `max_step_count_range` | (lo, hi) | (20, 160) | — | Execution step budget range |
| `jump_target_modes` | list | all | — | Behavior for out-of-range jump targets |
| `input_modes` | list | all | — | Input indexing mode (`direct` or `cyclic`) |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `input_mode` | `direct`, `cyclic` | Input indexing policy |
| `jump_target_mode` | `error`, `clamp`, `wrap` | Out-of-range jump handling |
| `max_step_count` | integer | Maximum VM steps before timeout status |
| `program.N.op` | instruction op names | Instruction opcode at index N |
| `program.N.target` | integer | Jump target index for jump instructions |

---

## FSM

Finite-state machines over integer sequences: `f(xs: list[int]) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `machine_types` | list | all | — | Machine family (`moore`, `mealy`) |
| `output_modes` | list | all | — | Output behavior (`final_state_id`, `accept_bool`, `transition_count`) |
| `undefined_transition_policies` | list | all | — | Behavior when no transition matches (`sink`, `stay`, `error`) |
| `predicate_types` | list | all | — | Predicate types used for transitions |
| `n_states_range` | (lo, hi) | (2, 6) | — | Range for number of states |
| `transitions_per_state_range` | (lo, hi) | (1, 4) | — | Range for transitions sampled per state |
| `target_difficulty` | int (1-5) | `None` | — | Optional target difficulty band |
| `value_range` | (lo, hi) | (-20, 20) | `--value-range` | Range used for query input values |
| `threshold_range` | (lo, hi) | (-10, 10) | `--threshold-range` | Range for threshold predicates |
| `divisor_range` | (lo, hi) | (2, 10) | `--divisor-range` | Range for modular predicates |

### Predicate Types

| Value | CLI | Description |
|-------|-----|-------------|
| `EVEN` | `even` | `x % 2 == 0` |
| `ODD` | `odd` | `x % 2 != 0` |
| `LT` | `lt` | `x < threshold` |
| `LE` | `le` | `x <= threshold` |
| `GT` | `gt` | `x > threshold` |
| `GE` | `ge` | `x >= threshold` |
| `MOD_EQ` | `mod_eq` | `x % divisor == remainder` |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `machine_type` | `moore`, `mealy` | FSM machine style |
| `output_mode` | output mode values | Output interpretation |
| `undefined_transition_policy` | `sink`, `stay`, `error` | Unmatched transition handling |
| `states.N.is_accept` | `true`, `false` | Acceptance bit for state N |
| `states.N.transitions.M.predicate.kind` | predicate types | Transition predicate type |
| `states.N.transitions.M.target_state_id` | integer | Transition target state id |

---

## Bitops

Fixed-width bit-operation pipelines over integer inputs: `f(x: int) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `target_difficulty` | int (1-5) | `None` | — | Optional target difficulty band |
| `width_choices` | list[int] | `[8, 16, 32]` | — | Allowed output bit widths |
| `n_ops_range` | (lo, hi) | (2, 6) | — | Range for sampled operation count |
| `value_range` | (lo, hi) | (-1024, 1024) | `--value-range` | Range for sampled integer inputs in queries |
| `mask_range` | (lo, hi) | (0, 65535) | — | Range for sampled mask arguments |
| `shift_range` | (lo, hi) | (0, 63) | — | Range for shift/rotate amounts |
| `allowed_ops` | list | all | — | Operations allowed during sampling |

### Operation Types

| Value | Description |
|-------|-------------|
| `and_mask` | `x & mask` |
| `or_mask` | `x \| mask` |
| `xor_mask` | `x ^ mask` |
| `shl` | Left shift |
| `shr_logical` | Logical right shift |
| `rotl` | Rotate left (within configured width) |
| `rotr` | Rotate right (within configured width) |
| `not` | Bitwise NOT (masked to configured width) |
| `popcount` | Number of set bits |
| `parity` | `popcount % 2` |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `width_bits` | integer | Active output width |
| `operations.N.op` | operation values | Opcode at instruction index N |
| `operations.N.arg` | integer | Immediate argument (when required by op) |

---

## Sequence DP

Sequence dynamic-programming alignment tasks:
`f(a: list[int], b: list[int]) -> int`

### Sampling Axes

| Axis | Type | Default | CLI Flag | Description |
|------|------|---------|----------|-------------|
| `target_difficulty` | int (1-5) | `None` | — | Optional target difficulty band |
| `templates` | list | all | — | DP template (`global`, `local`) |
| `output_modes` | list | all | — | Output selection (`score`, `alignment_len`, `gap_count`) |
| `predicate_types` | list | all | — | Matching predicate family |
| `len_a_range` | (lo, hi) | (2, 10) | `--list-length-range` | Range for sampled `a` lengths |
| `len_b_range` | (lo, hi) | (2, 10) | `--list-length-range` | Range for sampled `b` lengths |
| `value_range` | (lo, hi) | (-20, 20) | `--value-range` | Range for sampled values in both sequences |
| `match_score_range` | (lo, hi) | (1, 6) | — | Range for match score |
| `mismatch_score_range` | (lo, hi) | (-4, 1) | — | Range for mismatch score |
| `gap_score_range` | (lo, hi) | (-4, 0) | — | Range for gap score |
| `abs_diff_range` | (lo, hi) | (0, 5) | — | `max_diff` range for `abs_diff_le` predicates |
| `divisor_range` | (lo, hi) | (1, 10) | `--divisor-range` | Divisor range for `mod_eq` predicates |
| `tie_break_orders` | list | all | — | Priority order over `diag`, `up`, `left` moves |

### Predicate Types

| Value | Description |
|-------|-------------|
| `eq` | Pair matches when `a_i == b_j` |
| `abs_diff_le` | Pair matches when `abs(a_i - b_j) <= max_diff` |
| `mod_eq` | Pair matches when `(a_i - b_j) % divisor == remainder` |

### Spec Field Paths (for splits)

| Path | Values | Notes |
|------|--------|-------|
| `template` | `global`, `local` | DP initialization/reset semantics |
| `output_mode` | `score`, `alignment_len`, `gap_count` | Return value projection |
| `match_predicate.kind` | predicate types | Matching predicate type |
| `match_predicate.max_diff` | integer | Present for `abs_diff_le` |
| `match_predicate.divisor` | integer | Present for `mod_eq` |
| `match_predicate.remainder` | integer | Present for `mod_eq` |
| `match_score` | integer | Match transition delta |
| `mismatch_score` | integer | Mismatch transition delta |
| `gap_score` | integer | Gap transition delta |
| `step_tie_break` | tie-break enum values | Move priority under equal score |

---

## Using Spec Field Paths

Spec field paths use dot notation to access nested fields. List indices are supported.

```bash
# Hold out by template
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis template --holdout-value longest_run

# Hold out by nested predicate type
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis predicate.kind --holdout-value mod_eq

# Hold out first rule's predicate type (stringrules)
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis "rules.0.predicate.kind" --holdout-value starts_with

# Hold out numeric range
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis k --holdout-value "5,10" --holdout-type range
```

Holdout types:
- `exact` (default): Field value equals holdout value
- `range`: Field value in range (e.g., `"3,5"` for values 3-5)
- `contains`: Field value contains substring
