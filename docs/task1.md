# GOAL

Implement:
1) Predicate composition operators (not/and/or) for:
   - genfxn.core.predicates (numeric predicates)
   - genfxn.core.string_predicates (string predicates)
2) Transform pipelines for:
   - genfxn.core.transforms (numeric transforms)
   - genfxn.core.string_transforms (string transforms)

Keep full backwards compatibility:
- Old specs must still deserialize, evaluate, render, and validate.
- Do NOT change existing kind strings for existing atoms.
- Composition/pipeline should be additive.

## SCOPE / DESIGN CONSTRAINTS
A) Composition predicates:
- Implement kinds: "not", "and", "or"
- IMPORTANT: Keep it non-recursive for now (to reduce complexity):
  - not wraps an ATOMIC predicate (not a composed one)
  - and/or operands are a list of 2 or 3 ATOMIC predicates (no nested composed operands)
- Atomic numeric predicates are the existing ones: even/odd/lt/le/gt/ge/mod_eq/in_set
- Atomic string predicates are the existing ones: starts_with/ends_with/contains/is_alpha/is_digit/is_upper/is_lower/length_cmp

B) Transform pipelines:
- Implement kind: "pipeline"
- Pipeline steps are a list of 2 or 3 ATOMIC transforms (no nested pipelines)
- Atomic numeric transforms are existing ones: identity/abs/negate/shift/scale/clip
- Atomic string transforms are existing ones: identity/lowercase/uppercase/capitalize/swapcase/reverse/replace/strip/prepend/append

## IMPLEMENTATION TASKS (CODE)
1) core/predicates.py
   - Add Pydantic models: PredicateNot, PredicateAnd, PredicateOr (kind field values "not","and","or")
   - Add a PredicateAtom union for existing atomic predicate models
   - Update Predicate union to include the new composed models (discriminator="kind")
   - Update eval_predicate and render_predicate to support composed kinds
     - render must parenthesize correctly: "(a and b)", "(a or b)", "(not (a))" or similar
   - Update any helper functions if needed (e.g., get_threshold) to return None for composed.

2) core/string_predicates.py
   - Same as above for string predicates:
     - StringPredicateAtom union + StringPredicateNot/And/Or
   - Update eval_string_predicate and render_string_predicate accordingly (with parentheses)

3) core/transforms.py
   - Add TransformPipeline(kind="pipeline", steps: list[TransformAtom] with length 2..3)
   - Add TransformAtom union for existing atomic transform models
   - Update Transform union to include pipeline
   - Update eval_transform and render_transform:
     - eval: apply steps sequentially
     - render: nest expressions; if var is "x", apply t1 to "x" -> expr1; then t2 to expr1 -> expr2; etc.

4) core/string_transforms.py
   - Add StringTransformPipeline(kind="pipeline", steps: list[StringTransformAtom] length 2..3)
   - Update eval_string_transform and render_string_transform similarly.

5) Update AST safety where needed:
   - stringrules/ast_safety.py must allow boolean ops for composed predicates:
     - allow ast.BoolOp, ast.And, ast.Or, ast.Not (and ensure UnaryOp is OK)
   - stateful/ast_safety.py must allow BoolOp/And/Or/Not too (numeric predicate rendering may use them)

## TESTS
- Add unit tests in tests/test_core_dsl.py for:
  - numeric predicate composition eval/render (not/and/or)
  - numeric transform pipeline eval/render
- Add unit tests for string predicate composition + string transform pipeline (new file or extend tests/test_stringrules.py)
- Ensure existing tests still pass.

## NON-GOALS
- No “precedence conflict” sampling logic.
- No nested composed predicates beyond 3-atom and/or; no pipeline-of-pipeline.

## DELIVERABLE
A PR-quality implementation with:
- code changes
- tests added/updated
- `pytest` passing.
