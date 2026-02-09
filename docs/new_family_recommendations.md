# New Function Family Recommendations

Ranked by predicted semantic failure rate (description → reconstruction).

---

## 1. Finite State Machines (`fsm`)

**Predicted Failure Rate: Very High**

Functions that simulate FSMs processing an input sequence and producing output based on state transitions.

### Why It Fails

The description must capture the complete transition table. Natural language inherently loses information when describing combinatorial structures:
- "When in state A and the input is odd, move to B" x N transitions
- Models frequently miss edge transitions, invert conditions, or conflate similar states
- The more states/transitions, the more opportunities for partial reconstruction

### Example Spec

```python
{
    "states": ["A", "B", "C"],
    "initial": "A",
    "transitions": {
        ("A", "odd"): "B",
        ("A", "even"): "A",
        ("B", "odd"): "B",
        ("B", "even"): "C",
        ("C", "odd"): "A",
        ("C", "even"): "C"
    },
    "accept": ["C"],
    "output_mode": "final_state" | "accept_bool" | "transition_count"
}
```

### Difficulty Axes

- Number of states (2-5)
- Transition predicate complexity (parity, comparison, mod)
- Output mode (final state, accept/reject, count transitions, collect path)
- Reset conditions

---

## 2. Bit Manipulation (`bitops`)

**Predicted Failure Rate: Very High**

Functions combining bitwise operations in sequence or parallel.

### Why It Fails

Bit-level operations exist in a fundamentally different vocabulary than natural language:
- "The bits in odd positions" vs "every other bit starting from LSB" - ambiguous
- Describing XOR, rotation, masking in words is imprecise
- The gap between description and code is structural, not just a matter of detail

### Example Spec

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

### Difficulty Axes

- Number of operations (1-4)
- Operation types (mask, shift, rotate, popcount, leading/trailing zeros)
- Combine mode (sequential vs parallel aggregation)
- Mask complexity (fixed vs computed)

---

## 3. Nested Structure Traversal (`treeops`)

**Predicted Failure Rate: High**

Functions operating on nested lists representing trees with traversal, filtering, and aggregation.

### Why It Fails

Describing traversal order + depth conditions + leaf detection simultaneously creates compounding ambiguity:
- Preorder vs postorder vs level-order: easy to name, hard to verify understanding
- "Depth" is often off-by-one (is root depth 0 or 1?)
- Leaf vs internal node predicates interact with traversal order

### Example Spec

```python
{
    "traversal": "preorder" | "postorder" | "level_order",
    "node_predicate": {"kind": "depth_mod", "divisor": 2, "remainder": 0},
    "value_predicate": {"kind": "gt", "threshold": 0},
    "aggregation": "sum" | "max" | "count" | "collect",
    "target": "leaves" | "internal" | "all"
}
```

### Difficulty Axes

- Traversal order
- Depth predicates (exact, mod, range)
- Value predicates (comparison, parity)
- Aggregation type
- Node type filtering

---

## 4. Interval Operations (`intervals`)

**Predicted Failure Rate: High**

Merge, split, find gaps, count overlaps on interval collections.

### Why It Fails

Boundary semantics are notoriously subtle:
- Closed vs open endpoints: `[1, 3]` vs `[1, 3)` vs `(1, 3]`
- "Overlapping" vs "touching" vs "containing" - descriptions conflate these
- Edge cases pass most tests but fail on boundary conditions

### Example Spec

```python
{
    "operation": "merge" | "find_gaps" | "count_overlaps" | "split_at",
    "boundary_mode": "closed_closed" | "closed_open" | "open_closed" | "open_open",
    "merge_touching": true | false,
    "sort_output": true | false,
    "output": "intervals" | "total_coverage" | "max_overlap_count"
}
```

### Difficulty Axes

- Operation type
- Boundary semantics
- Touching vs overlapping distinction
- Output format
- Empty interval handling

---

## 5. Custom Tokenizer/Parser (`miniparse`)

**Predicted Failure Rate: Medium-High**

Tokenize or evaluate simple expressions with custom operator definitions.

### Why It Fails

Precedence and associativity interactions are subtle:
- Left vs right associativity for a single operator is frequently missed
- `2^3^4` = `2^(3^4)` vs `(2^3)^4` - easy to get wrong
- Unary operators add another layer of complexity

### Example Spec

```python
{
    "operators": [
        {"symbol": "+", "precedence": 1, "associativity": "left"},
        {"symbol": "*", "precedence": 2, "associativity": "left"},
        {"symbol": "^", "precedence": 3, "associativity": "right"}
    ],
    "unary": [{"symbol": "-", "precedence": 4}],
    "output": "tokens" | "postfix" | "ast" | "evaluate"
}
```

### Difficulty Axes

- Number of operators (2-5)
- Precedence levels
- Associativity mix (all left, all right, mixed)
- Unary operators
- Output format

---

## 6. Multi-Key Sorting (`ranking`)

**Predicted Failure Rate: Medium**

Sort by computed keys with complex tie-breaking and stability.

### Why It Fails

Multi-level comparisons with mixed directions are easy to implement but hard to describe:
- "Sort by X ascending, then by Y descending, then by original position"
- Stability requirements are often implicit and lost
- Key extraction functions add another layer of potential misunderstanding

### Example Spec

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

### Difficulty Axes

- Number of sort keys (1-4)
- Key extraction complexity (identity, digit extraction, mod, predicate count)
- Direction mix
- Output format (values, indices, ranks)
- Stability requirement

---

## 7. Grid/Cellular Operations (`grid`)

**Predicted Failure Rate: Medium**

Functions on 2D grids: neighbor counting, flood fill, path queries.

### Why It Fails

Spatial reasoning + boundary handling + connectivity rules compound:
- 4-connected vs 8-connected vs custom neighborhoods
- Boundary handling (wrap, zero-pad, clamp, error)
- "Reachable" definitions vary

### Example Spec

```python
{
    "operation": "count_neighbors" | "flood_fill" | "reachable_count" | "shortest_path",
    "neighborhood": "4-connected" | "8-connected" | "knight_move",
    "cell_predicate": {"kind": "value_gt", "threshold": 0},
    "boundary": "wrap" | "zero" | "clamp" | "error",
    "output": "count" | "mask" | "coordinates"
}
```

### Difficulty Axes

- Operation type
- Neighborhood definition
- Boundary handling
- Cell predicates
- Output format

---

## Implementation Priority

Based on failure rate × implementation effort:

| Priority | Family | Failure Rate | Implementation Effort |
|----------|--------|--------------|----------------------|
| 1 | `fsm` | Very High | Medium |
| 2 | `bitops` | Very High | Low-Medium |
| 3 | `intervals` | High | Low |
| 4 | `treeops` | High | Medium |
| 5 | `ranking` | Medium | Low |
| 6 | `miniparse` | Medium-High | Medium-High |
| 7 | `grid` | Medium | Medium |

The top 3 (`fsm`, `bitops`, `intervals`) offer the best tradeoff: high semantic failure rates with reasonable implementation complexity.
