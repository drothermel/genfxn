
# GOAL
Implement the rest of the difficulty-expansion changes so that:
- stringrules supports D3/D4/D5 with new composition + pipelines
- stateful supports D3/D4/D5 by adding value_transform and a new toggle_sum template
- simple_algorithms supports D3/D4/D5 by adding preprocess (filter/transform), new edge behaviors, and extended difficulty scoring

## CRITICAL CONSTRAINT
Do NOT change difficulty buckets for existing sampled specs.
- Existing atom scoring remains identical.
- Any new scoring only applies to the newly added kinds/fields.

## PART A — Update difficulty scoring (genfxn/core/difficulty.py)
1) Numeric predicate scoring (_predicate_score):
   - keep existing:
     even/odd ->1
     lt/le/gt/ge ->2
     in_set ->3
     mod_eq ->4
   - new:
     not/and/or -> 5

2) Numeric transform scoring (_transform_score):
   - keep existing:
     identity ->1
     abs/negate ->2
     shift/scale/clip ->3
   - new pipeline scoring:
     Define "parameterized" numeric transform steps as {shift, scale, clip}.
     For pipeline(kind="pipeline", steps=[...]):
       - len==2 and param_steps==0 -> 3
       - len==2 and param_steps>=1 -> 4
       - len==3 OR param_steps>=2 -> 5

3) String predicate scoring (_string_predicate_score):
   - keep existing atom scoring:
     is_* ->1
     starts/ends/contains ->2
     length_cmp eq/le/ge ->2
     length_cmp lt/gt ->3
   - new:
     not(atom) ->4
     and/or with 2 atoms ->4
     and/or with 3 atoms ->5

4) String transform scoring (_string_transform_score):
   - keep existing:
     identity ->1
     case/reverse ->2
     replace/strip/prepend/append ->3
   - new pipeline scoring:
     Define "parameterized" string transform steps as {replace, strip, prepend, append}.
     For pipeline steps:
       - len==2 and param_steps==0 -> 3
       - len==2 and param_steps>=1 -> 4
       - len==3 OR param_steps>=2 -> 5

5) Update transform/predicate collection helpers:
   - stateful: include new value_transform (resetting) and new toggle_sum transforms
   - stringrules: scoring already averages across per-rule predicates/transforms; pipeline/composition will be encoded in kind fields

Add/extend tests in tests/test_difficulty.py to cover the new kinds.

## PART B — Stringrules: expand generation range
1) genfxn/stringrules/models.py
   - Increase StringRulesAxes.n_rules max from 8 to 10 (Field le=10)
2) genfxn/core/presets.py
   - Add STRINGRULES_PRESETS for difficulty 5 (keys=5) with multiple variants so generation can produce D5.
   - Variants should include different n_rules values in {6,7,8,10} and include the new predicate/transform types that enable composition/pipeline.

3) genfxn/stringrules/sampler.py
   - Add support for sampling composed predicates and pipeline transforms (if not already covered in prompt 1 wiring):
     - Add new enum values to StringPredicateType and StringTransformType as needed (e.g., NOT/AND/OR and PIPELINE)
     - Sampling composed predicate: pick operator, pick 2 or 3 atomic predicate atoms
     - Sampling pipeline transform: pick 2 or 3 atomic transform steps
   - Ensure overlap logic still works reasonably (no need for precedence-conflict guarantees)

4) genfxn/stringrules/queries.py
   - Update _generate_matching_string/_generate_non_matching_string to handle composed predicates:
     - easiest: fallback to randomized search that checks eval_string_predicate(pred, s) until it matches (with attempt caps)
   - Keep existing atomic fast-path generation.

5) genfxn/stringrules/ast_safety.py
   - Ensure BoolOp/And/Or/Not are allowed (if not already).

## PART C — Stateful: add value_transform and toggle_sum template
1) genfxn/stateful/models.py
   - Add value_transform: Transform | None to ResettingBestPrefixSumSpec (default None meaning identity)
   - Add a new TemplateType "toggle_sum"
   - Add ToggleSumSpec with fields:
       toggle_predicate: Predicate
       on_transform: Transform
       off_transform: Transform
       init_value: int (keep existing range semantics)
     Semantics:
       on = False
       acc = init_value
       for x in xs:
         if eval_predicate(toggle_predicate, x): on = not on
         acc += eval_transform(on_transform if on else off_transform, x)
       return acc

2) Update stateful/eval.py, stateful/render.py, stateful/sampler.py, stateful/queries.py
   - eval: implement the new template and apply value_transform for resetting:
     - when reset_predicate triggers, reset current_sum to init_value
     - otherwise add eval_transform(value_transform or identity, x)
   - render: generate readable python code consistent with ast_safety
   - sampler: sample new fields using axes
   - queries: ensure no crashes; for composed predicates/pipelines, allow fallback random search for matching/nonmatching values

3) Update stateful/ast_safety.py
   - allow BoolOp/And/Or/Not
   - allow variable name "on" for toggle_sum

4) genfxn/core/presets.py
   - Extend STATEFUL_PRESETS with difficulty 4 and 5:
     - D4 should include conditional w/ pipelines or composed predicate; and resetting w/ value_transform; plus some toggle_sum
     - D5 should include toggle_sum and resetting with composed predicate + pipeline5 transforms

## PART D — Simple Algorithms: preprocess + new edge behaviors + D4/D5
1) genfxn/simple_algorithms/models.py
   - Add preprocess fields to all specs (base mixin):
       pre_filter: Predicate | None
       pre_transform: Transform | None
   - Add new edge fields:
     - MostFrequentSpec: tie_default: int | None
       Semantics: if tie for most frequent and tie_default is not None, return tie_default (override tie_break)
     - CountPairsSumSpec: no_result_default: int | None; short_list_default: int | None
       Semantics:
         - if len(xs) < 2 and short_list_default is not None: return short_list_default
         - if no pairs found and no_result_default is not None: return no_result_default
     - MaxWindowSumSpec: empty_default: int | None
       Semantics:
         - if xs is empty and empty_default is not None: return empty_default
         - else keep legacy invalid_k_default behavior for len(xs) < k

   Backwards compatibility:
   - If new fields are None, behavior should match current behavior exactly.

2) genfxn/simple_algorithms/eval.py + render.py + sampler.py + queries.py
   - Apply preprocess first:
       ys = xs
       if pre_filter: ys = [x for x in ys if eval_predicate(pre_filter,x)]
       if pre_transform: ys = [eval_transform(pre_transform,x) for x in ys]
   - Then run the algorithm on ys.
   - Update render to include the preprocess stage.
   - Update queries to include at least some adversarial cases that can trigger:
       - ties (most_frequent)
       - no pairs / short list (count_pairs_sum)
       - empty list (max_window_sum)

3) genfxn/core/presets.py
   - Add SIMPLE_ALGORITHMS_PRESETS for difficulty 4 and 5 that enable preprocess + new edge fields + pipelines.

4) Extend simple_algorithms difficulty in genfxn/core/difficulty.py
   - Keep EXACT legacy behavior when preprocess is absent AND all new edge fields are None:
       use current scoring untouched.
   - Otherwise use extended component scores:
     a) template_score:
        base: most_frequent=2, count_pairs_sum=3, max_window_sum=3
        +1 if preprocess has either filter or transform
        +1 if preprocess has both filter and transform
        +1 if pre_transform is a pipeline with score 5 (cap at 5)
     b) mode_score:
        base_mode as today
        preprocess_score = max(filter_score, transform_score) where:
          - filter_score: comparison=2, mod_eq=4, composed=5, none=1
          - transform_score: atomic non-identity=3, pipeline4=4, pipeline5=5, none=1
        mode_score = max(base_mode, preprocess_score)
     c) edge_score:
        edge_count = number of enabled edge behaviors with non-default values:
          - treat a field as enabled if value is not None AND value != 0
          - invalid_k_default counts if != 0 (legacy)
          - empty_default counts if != 0
          - tie_default counts if != 0
          - no_result_default counts if != 0
          - short_list_default counts if != 0
        edge_score = min(5, 1 + edge_count)

     raw = 0.5*template_score + 0.3*mode_score + 0.2*edge_score
     difficulty = clamp(round(raw), 1, 5)

## TESTS / SANITY
- Update/add tests so `pytest` passes.
- Add a small smoke test that samples ~200 specs at each of (family, D3/D4/D5) and asserts that:
  - compute_difficulty hits the intended bucket with non-trivial frequency
  - old specs from existing fixtures remain unchanged.

## NON-GOALS
- No precedence-conflict reachability constraints for stringrules.
- No nested predicate composition beyond 3-atom and/or, and no nested pipelines.
