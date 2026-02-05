# GOAL
Create a new suite-generation pipeline that produces, for EACH family in:
  - stringrules
  - stateful
  - simple_algorithms

and EACH difficulty in {3,4,5}:
  - exactly 50 tasks selected to meet the quota tables below

Output directory structure should mirror existing paper_splits:
  data/balanced_suites/{family}/level_{d}/all.jsonl

Optionally also emit train/test splits, but all.jsonl is required.

IMPORTANT: Do NOT “take first N”.
Generate a big candidate pool, then SELECT using quotas.

## FIX REPRODUCIBILITY BUG
Do not use Python’s hash() for seeding (hash randomization).
Use a stable seed derivation, e.g.:
  stable = zlib.crc32(f"{seed}:{family}:{difficulty}:{pool_index}".encode())
or sha256 -> int.

## QUOTA TABLES (HARD REQUIREMENTS)
### STRINGRULES
D3 (50):
- constraints: has_comp=False, has_pipe=False
- n_rules_bucket: 4–5:20, 6–7:20, 8–10:10
- pred_majority: simple:20, pattern:20, length-heavy:10
- transform_majority: identity-heavy:10, simple-heavy:20, param-heavy:20

D4 (50):
- constraint: has_comp XOR has_pipe
- mode: comp-only:25, pipe-only:25
- n_rules_bucket: 4–5:10, 6–7:20, 8–10:20
- within comp-only: comp_max_score 4:15, 5:10
- within pipe-only: pipe_max_score 4:15, 5:10

D5 (50):
- constraints: has_comp=True, has_pipe=True, comp_rate>=0.6, pipe_rate>=0.6
- n_rules_bucket: 4–5:10, 6–7:20, 8–10:20
- comp_max_score: 4:20, 5:30
- pipe_max_score: 4:20, 5:30

### STATEFUL
D3 (50):
- constraints: no pipelines, no composed predicates, no toggle_sum
- template: conditional:35, resetting:15
- pred_kind: comparison:25, mod_eq:25
- conditional transform signature: both_affine:15, both_sign:10, mixed:10

D4 (50):
- template: conditional:25, resetting:15, toggle_sum:10
- pred_kind: mod_eq:25, composed:15, comparison:10
- transform_bucket: atomic_nonidentity:25, pipeline4:20, pipeline5:5

D5 (50):
- constraints: template in {toggle_sum, resetting}; pipeline5 for all transforms; resetting must have composed predicate
- template: toggle_sum:25, resetting:25
- pred_kind: mod_eq:25, composed:25
- transform_bucket: pipeline5:50

### SIMPLE_ALGORITHMS
D3 (50):
- constraint: preprocess_bucket=none
- template: count_pairs_sum:25, max_window_sum:25
- within count_pairs_sum: target_sign neg:10, zero:5, pos:10
- within max_window_sum: k_bucket 6–7:12, 8–10:13

D4 (50):
- constraint: preprocess present in all
- template: most_frequent:15, count_pairs_sum:20, max_window_sum:15
- preprocess_bucket: filter_only:15, transform_only:15, both:20
- filter_kind (within the 35 with filter): comparison:10, mod_eq:15, composed:10
- pre_transform_complexity (within the 35 with transform): atomic:10, pipeline4:25
- edge_count: 1:40, 2:10

D5 (50):
- constraints: preprocess_bucket=both, pre_transform=pipeline5, edge_count=2
- template: most_frequent:15, count_pairs_sum:20, max_window_sum:15
- filter_kind: mod_eq:25, composed:25
- pre_transform_complexity: pipeline5:50
- edge_count: 2:50

## IMPLEMENTATION PLAN
1) Create feature extraction functions (pure, deterministic) for each family:
   - stringrules_features(spec) -> dict[str,str|int|float] including:
     n_rules_bucket, has_comp, has_pipe, mode, comp_max_score, pipe_max_score,
     comp_rate, pipe_rate, pred_majority, transform_majority
   - stateful_features(spec) -> includes template, pred_kind, transform_bucket, etc.
   - simple_algorithms_features(spec) -> includes template, preprocess_bucket, filter_kind,
     pre_transform_complexity, edge_count, etc.

2) Create quota table definitions in code (e.g., genfxn/suites/quotas.py) using the exact numbers above.

3) Implement a greedy selector:
   - Generate a candidate pool size like 2000–5000 per (family,difficulty), deterministic seed.
   - Keep only candidates with compute_difficulty(family,spec)==difficulty.
   - Apply hard constraints for that (family,difficulty) before selection.
   - Greedy selection heuristic:
     At each step pick the candidate that reduces the largest total quota deficit
     across all tracked axes (weighted sum).
   - Ensure no duplicate task_ids.
   - If you fail to meet quotas, increase pool size automatically and retry (bounded retries).

4) Add a CLI script:
   scripts/generate_balanced_suites.py
   Options: --output_dir, --seed, --pool_size, --families, --difficulties

5) Print a quota satisfaction report:
   - For each axis: achieved counts vs required counts
   - Also show min/max/avg difficulty raw score if convenient

6) Add tests:
   - Small pool size smoke test (e.g., 300 candidates) with relaxed quotas or just verify
     that features extraction works and hard constraints filter correctly.
   - Full quota tests can be marked slow or optional.

## DELIVERABLE
- New script + quota definitions + feature extraction + greedy selection
- Balanced suites generated deterministically
- Tests passing.
