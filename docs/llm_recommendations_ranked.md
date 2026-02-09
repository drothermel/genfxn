# Function Family Recommendations (Ranked)

Ranked by predicted semantic failure rate (description → reconstruction), highest to lowest.
Date: 2026-02-09

1. Stack/Bytecode Interpreter
**Predicted failure:** Very high.
Signature: `f(xs: list[int]) -> int` (top of stack) or `-> list[int]`.
Why: control flow, stack effects, and jumps create compounding, non-local mistakes that are hard to describe and easy to mis-implement.
Testing: reference interpreter with randomized inputs and coverage for each opcode + jump branch.

2. Finite-State Transducer (Mealy/Moore)
**Predicted failure:** Very high.
Signature: `f(xs: list[int]) -> list[int]` or `-> int`.
Why: transition tables and per-transition outputs are dense; omissions and condition inversions are common.
Testing: simulate on sequences that hit every transition plus random sequences.

3. Sequence DP With Custom Scoring
**Predicted failure:** High.
Signature: `f(a: list[int], b: list[int]) -> int` (score) or `-> list[int]` (alignment).
Why: DP recurrence + base cases + tie-break semantics produce subtle, systematic errors.
Testing: reference DP on random pairs plus short cases that force ties.

4. Graph Query Functions
**Predicted failure:** High.
Signature: `f(u: int, v: int) -> int` or `-> bool`.
Why: global structure reasoning (reachability, shortest path, constrained paths) is easy to describe but frequently mis-specified.
Testing: BFS/DFS/Dijkstra on small graphs; query all node pairs.

5. Cellular Automaton / Iterated Rule System
**Predicted failure:** High.
Signature: `f(grid: list[list[int]]) -> list[list[int]]` or `-> int`.
Why: repeated local updates, boundary conditions, and step counts produce off-by-one and edge errors.
Testing: exact simulation on random grids plus known patterns.

6. Temporal Logic Over Streams
**Predicted failure:** Medium-high.
Signature: `f(xs: list[int]) -> bool`.
Why: temporal operators (“eventually”, “until”) are semantically nuanced and frequently misinterpreted.
Testing: brute-force evaluator for generated sequences and targeted counterexamples.

7. Recursive Definitions With Memoization Quirks
**Predicted failure:** Medium-high.
Signature: `f(n: int) -> int`.
Why: base case handling + conditional resets/threshold quirks are easy to miss.
Testing: compute reference sequence up to N and check exact outputs.

8. Arithmetic on Mixed Bases / Digit-Level Transforms
**Predicted failure:** Medium-high.
Signature: `f(n: int) -> int`.
Why: base conversion, digit transforms, and carry rules are easy to misstate or reorder.
Testing: evaluate on random integers in range and edge values.

9. Sequence Functions With Local + Global Constraints
**Predicted failure:** Medium.
Signature: `f(xs: list[int]) -> int` or `-> list[int]`.
Why: multi-pass logic that mixes adjacency rules with global conditions is error-prone.
Testing: random sequences plus adversarial edge cases.

10. Higher-Order Function Composition
**Predicted failure:** Medium.
Signature: `f(x: int) -> int` or `f(xs: list[int]) -> list[int]`.
Why: ordering of primitives and interaction effects are often misapplied.
Testing: evaluate composed pipeline on random inputs.

11. String Transducers With Overlapping Rules
**Predicted failure:** Medium.
Signature: `f(s: str) -> str`.
Why: rule ordering and overlap semantics cause common mistakes.
Testing: generate strings that trigger first-match and shadowed rules.
Note: overlaps with existing `stringrules`.

12. Piecewise With Nontrivial Region Logic
**Predicted failure:** Medium-low.
Signature: `f(x: int) -> int`.
Why: Boolean region logic adds some complexity, but still local and easily testable.
Testing: brute-force over input range.
Note: overlaps with existing `piecewise`.

13. Probabilistic-but-Deterministic via Seed
**Predicted failure:** Medium-low.
Signature: `f(x: int) -> int` or `f(xs: list[int]) -> list[int]`.
Why: if PRNG and seeding are explicit, implementation is mostly mechanical.
Testing: fixed seed + deterministic PRNG reference.

14. Constraint-Satisfaction Outputs (Witness)
**Predicted failure:** Low.
Signature: `f(n: int) -> list[int]` or `-> str`.
Why: spec is usually simple (“any witness satisfying constraints”), so reconstruction is less fragile.
Testing: verifier that checks constraints only.

15. Algebraic Structures With Custom Ops
**Predicted failure:** Low.
Signature: `f(xs: list[int]) -> int`.
Why: table-driven operations are straightforward if the op table is explicit.
Testing: direct evaluation using the op table.
