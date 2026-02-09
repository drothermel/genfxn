# Recommended Merged Family List

Combined recommendations from two independent analyses, ranked by predicted semantic failure rate in a describe → reconstruct pipeline.

---

## Tier 1: Very High Failure Rate

### 1. Stack/Bytecode Interpreter (`bytecode`)

Functions that simulate a small stack machine executing bytecode instructions with jumps, conditionals, and stack effects.

**Why it tops the list:** Non-local control flow (jumps, conditional branches) means the description must convey global program structure, not just local rules. Models must reason about instruction pointer movement, stack depth, and operand ordering simultaneously.

**Spec sketch:**
```python
{
    "instructions": ["PUSH", "ADD", "DUP", "JUMP_IF_ZERO", "POP", "SWAP"],
    "program": [("PUSH", 3), ("PUSH", 5), ("ADD",), ("DUP",), ("JUMP_IF_ZERO", 0)],
    "input_mode": "stack_init" | "stdin_sequence",
    "output_mode": "top_of_stack" | "full_stack" | "stdout_collect"
}
```

**Difficulty axes:** Instruction set size, control flow depth (linear, single branch, loops), stack depth, output mode.

---

### 2. Finite-State Transducer (`fst`)

Functions implementing Mealy or Moore machines that both transition between states and produce output on each transition or in each state.

**Why it's hard:** Must describe the full transition table AND the output function. Two parallel mappings over the same state space. Descriptions almost always lose at least one transition or output assignment.

**Spec sketch:**
```python
{
    "machine_type": "mealy" | "moore",
    "states": ["A", "B", "C"],
    "initial": "A",
    "transitions": {("A", "odd"): "B", ("A", "even"): "A", ...},
    "outputs": {("A", "odd"): 1, ...},
    "accept": ["C"]
}
```

**Difficulty axes:** Number of states, input alphabet size, machine type, output complexity.

---

### 3. Bit Manipulation (`bitops`)

Functions chaining bitwise operations: masking, shifting, rotation, popcount, with conditional logic.

**Why it's hard:** Bit-level operations exist in a fundamentally different vocabulary than natural language. Descriptions of masks, rotations, and XOR conditions are inherently lossy when verbalized. The translation gap is structural.

**Spec sketch:**
```python
{
    "operations": [
        {"op": "mask_and", "mask": 0b10101010},
        {"op": "popcount"},
        {"op": "xor_with", "value": 0x0F},
        {"op": "rotate_left", "amount": 3}
    ],
    "combine_mode": "chain" | "parallel_reduce",
    "final_transform": "identity" | "to_bool" | "mod"
}
```

**Difficulty axes:** Number of operations, operation types, combine mode, mask complexity.

---

## Tier 2: High Failure Rate

### 4. Sequence DP With Custom Scoring (`seqdp`)

Functions computing dynamic programming recurrences over sequences with custom scoring, base cases, and tie-breaking.

**Why it's hard:** DP recurrences require specifying the subproblem structure, transition formula, base cases, and optimization direction. Each is a source of error. Alignment-style problems with gap penalties and match bonuses have many near-identical variants that differ in subtle ways.

**Spec sketch:**
```python
{
    "recurrence_type": "longest_subsequence" | "alignment" | "partition",
    "score_fn": {"match": 2, "mismatch": -1, "gap": -2},
    "base_case": "zero" | "negative_inf" | "custom",
    "tie_break": "first" | "last" | "lexicographic",
    "output": "score" | "solution" | "count"
}
```

**Difficulty axes:** Recurrence type, scoring function complexity, base case handling, tie-breaking, output mode.

---

### 5. Interval Operations (`intervals`)

Merge, split, find gaps, count overlaps on interval collections with varying boundary semantics.

**Why it's hard:** Boundary semantics (open/closed, touching/overlapping/containing) are notoriously subtle. Descriptions frequently conflate these, and edge cases tend to pass most test inputs but fail on boundaries.

**Spec sketch:**
```python
{
    "operation": "merge" | "find_gaps" | "count_overlaps" | "split_at",
    "boundary_mode": "closed_closed" | "closed_open" | "open_closed" | "open_open",
    "merge_touching": true | false,
    "output": "intervals" | "total_coverage" | "max_overlap_count"
}
```

**Difficulty axes:** Operation type, boundary semantics, touching vs overlapping distinction, output format.

---

### 6. Temporal Logic Over Streams (`temporal`)

Functions evaluating temporal-logic-like operators (eventually, always, until, since) over input sequences.

**Why it's hard:** Temporal operators have precise formal semantics that natural language approximates poorly. "Eventually X" vs "X holds at some future point" vs "X before the end" sound equivalent but can differ on edge cases (empty sequences, single-element sequences).

**Spec sketch:**
```python
{
    "formula": {"op": "until", "left": {"op": "gt", "value": 0}, "right": {"op": "eq", "value": 0}},
    "quantifier": "exists" | "forall",
    "window": null | 5,
    "output": "bool" | "first_index" | "count_satisfying"
}
```

**Difficulty axes:** Formula depth, operator mix, windowed vs unbounded, output mode.

---

### 7. Graph Query Functions (`graphquery`)

Functions answering constrained queries over graphs: reachability with constraints, weighted shortest paths, cycle detection with conditions.

**Why it's hard:** Graph reasoning requires global structural understanding. Describing path constraints, edge filtering, and aggregation over paths produces long descriptions where information loss is almost guaranteed. The non-local nature of graph properties (reachability, shortest paths) means a single missed constraint invalidates the entire reconstruction.

**Spec sketch:**
```python
{
    "query": "reachable" | "shortest_path" | "cycle_exists" | "connected_components",
    "edge_predicate": {"kind": "weight_lt", "threshold": 5},
    "path_constraint": "max_hops" | "no_revisit" | "monotone_weight",
    "output": "bool" | "path" | "count" | "cost"
}
```

**Difficulty axes:** Query type, edge predicates, path constraints, graph density, output mode.

---

### 8. Grid/Cellular Operations (`grid`)

Functions on 2D grids: neighbor counting, flood fill, iterated cellular automaton rules, path queries.

**Why it's hard:** Spatial reasoning + boundary handling + connectivity rules compound. When rules are applied iteratively (cellular automaton style), errors in boundary handling or neighborhood definition compound across steps, making multi-step variants substantially harder than single-step queries.

**Spec sketch:**
```python
{
    "operation": "count_neighbors" | "flood_fill" | "step_automaton",
    "neighborhood": "4-connected" | "8-connected" | "knight_move",
    "boundary": "wrap" | "zero" | "clamp",
    "iterations": 1 | 3 | 10,
    "output": "grid" | "count" | "coordinates"
}
```

**Difficulty axes:** Operation type, neighborhood, boundary handling, iteration count, cell predicates.

---

### 9. Nested Structure Traversal (`treeops`)

Functions operating on nested lists representing trees with traversal order, depth predicates, and aggregation.

**Why it's hard:** Describing traversal order + depth conditions + leaf detection simultaneously creates compounding ambiguity. Off-by-one on depth is extremely common.

**Spec sketch:**
```python
{
    "traversal": "preorder" | "postorder" | "level_order",
    "node_predicate": {"kind": "depth_mod", "divisor": 2, "remainder": 0},
    "aggregation": "sum" | "max" | "count" | "collect",
    "target": "leaves" | "internal" | "all"
}
```

**Difficulty axes:** Traversal order, depth predicates, value predicates, aggregation type, node type filtering.

---

## Tier 3: Medium-High Failure Rate

### 10. Custom Tokenizer/Parser (`miniparse`)

Tokenize or evaluate expressions with custom operator precedence and associativity.

**Why it's hard:** Precedence x associativity interactions are subtle. Left vs right associativity for a single operator is frequently missed or inverted during reconstruction.

**Spec sketch:**
```python
{
    "operators": [
        {"symbol": "+", "precedence": 1, "associativity": "left"},
        {"symbol": "^", "precedence": 3, "associativity": "right"}
    ],
    "output": "tokens" | "postfix" | "evaluate"
}
```

**Difficulty axes:** Number of operators, precedence levels, associativity mix, unary operators, output format.

---

### 11. Mixed Bases / Digit Transforms (`digitops`)

Functions performing arithmetic or transforms on numbers in custom or mixed bases, or operating digit-by-digit with varying rules per position.

**Why it's hard:** Base conversion and position-dependent rules share the "different vocabulary" problem of bitops. Carry propagation in non-standard bases is a frequent failure point.

**Spec sketch:**
```python
{
    "base": 7 | "mixed",
    "digit_rule": [
        {"position": "even", "transform": "add", "value": 1},
        {"position": "odd", "transform": "multiply", "value": 2}
    ],
    "carry_mode": "standard" | "no_carry" | "wrap",
    "output": "digits" | "decimal_value"
}
```

**Difficulty axes:** Base, digit rule complexity, carry semantics, output format.

---

## Tier 4: Medium Failure Rate

### 12. Multi-Key Sorting (`ranking`)

Sort by computed keys with complex tie-breaking and stability requirements.

**Why it's hard:** Multi-level comparisons with mixed ascending/descending directions are easy to implement but hard to describe unambiguously. Stability is often implicit and lost in translation.

**Spec sketch:**
```python
{
    "keys": [
        {"extract": "digit_at", "position": 1, "direction": "asc"},
        {"extract": "mod", "divisor": 3, "direction": "desc"},
        {"extract": "original_index", "direction": "asc"}
    ],
    "output": "sorted_values" | "sorted_indices" | "ranks"
}
```

**Difficulty axes:** Number of sort keys, key extraction complexity, direction mix, stability.

---

## Implementation Roadmap

| Phase | Families | Rationale |
|-------|----------|-----------|
| Phase 1 | `fst`, `bitops`, `intervals` | Highest failure rate with lowest implementation complexity. Closest to existing family structure. |
| Phase 2 | `bytecode`, `seqdp`, `graphquery` | High failure rate, moderate implementation effort. `bytecode` requires a mini VM; `graphquery` needs graph construction utilities. |
| Phase 3 | `temporal`, `grid`, `treeops` | Strong failure modes. `grid` with iterated rules compounds errors across steps. All three need more complex test generation. |
| Phase 4 | `miniparse`, `digitops`, `ranking` | Solid additions that round out the difficulty spectrum. |
