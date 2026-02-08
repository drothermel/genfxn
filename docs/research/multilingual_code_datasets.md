# Multilingual Code Datasets Survey

Surveyed 2026-02-08 to inform which languages to add to genfxn.

## Summary Table

| Dataset | Year | # PLs | Python+Java | Rust | Parallel | Scale | Task Type |
|---------|------|-------|-------------|------|----------|-------|-----------|
| MultiPL-E | 2022 | 27 | Yes | Yes | Yes | ~1138/lang | Generation |
| HumanEval-X | 2023 | 5-6 | Yes | v2 only | Yes | 164/lang | Generation + Translation |
| MBXP | 2023 | 13 | Yes | No | Yes | ~974/lang | Generation |
| McEval | 2025 | 40 | Yes | Yes | No | ~50/lang (gen) | Gen + Explain + Completion |
| CRUXEval-X | 2025 | 19 | Yes | Yes | Yes | ~600/lang | Reasoning (I/O prediction) |
| HumanEval-XL | 2024 | 12 PL x 23 NL | Yes | No | Yes | 22,080 total | Generation (cross-NL) |
| AutoCodeBench | 2025 | 20 | Yes | Yes | Yes | ~196/lang | Generation (hard) |
| XLCoST | 2022 | 7 | Yes | No | Yes | thousands | Translation + Search |
| AVATAR | 2021 | 2 | Yes | No | Yes | 9,515 | Translation (Java<->Python) |
| CodeTransOcean | 2023 | 45 | Yes | Likely | Yes | varies | Translation |
| CRUST-Bench | 2025 | 2 (C->Rust) | No | Yes | Yes | 100 repos | Translation |
| RustRepoTrans | 2024 | 4 (->Rust) | Yes (source) | Yes (target) | Yes | repo-level | Translation |

## Dataset Details

### MultiPL-E
- **Languages**: 27 PLs including Python, Java, JavaScript, C++, Rust, Go, TypeScript, C#, and many more
- **Parallel?**: Yes — same problems auto-transpiled from Python HumanEval (164) and MBPP (974)
- **Task**: Code generation (function completion with unit tests)
- **Links**: [GitHub](https://github.com/nuprl/MultiPL-E), [HuggingFace](https://huggingface.co/datasets/nuprl/MultiPL-E), [Paper](https://arxiv.org/abs/2208.08227)

### HumanEval-X (CodeGeeX)
- **Languages**: Python, C++, Java, JavaScript, Go (CodeGeeX2 added Rust)
- **Parallel?**: Yes — 164 problems hand-crafted in each language (higher quality than auto-transpiled)
- **Task**: Code generation + code translation
- **Links**: [HuggingFace](https://huggingface.co/datasets/THUDM/humaneval-x), [Paper](https://arxiv.org/abs/2303.17568)

### MBXP (Amazon)
- **Languages**: 13 PLs — Python, Java, JavaScript, TypeScript, Go, Ruby, Kotlin, PHP, C#, Scala, C++, Swift, Perl
- **Parallel?**: Yes — auto-transpiled from MBPP/HumanEval
- **Task**: Code generation (function completion)
- **Links**: [GitHub](https://github.com/amazon-science/mxeval), [Paper (ICLR 2023)](https://openreview.net/forum?id=Bo7eeXm6An8)

### McEval
- **Languages**: 40 PLs including Python, Java, JavaScript, C++, Rust, and many niche languages
- **Parallel?**: No — independently authored per language, captures language-specific idioms
- **Task**: Code generation, explanation, completion
- **Links**: [Website](https://mceval.github.io/), [Paper](https://arxiv.org/abs/2406.07436), [GitHub](https://github.com/MCEVAL/McEval)

### CRUXEval-X
- **Languages**: 19 PLs — Python, Java, JavaScript, C++, Rust, Go, C#, TypeScript, and more
- **Parallel?**: Yes — auto-translated via test-guided pipeline
- **Task**: Code reasoning (input/output prediction, not generation)
- **Notes**: Most relevant to genfxn's function-level reasoning focus. Tests whether models can trace execution across languages.
- **Links**: [Paper](https://arxiv.org/abs/2408.13001), [GitHub](https://github.com/CRUXEVAL-X/cruxeval-x)

### HumanEval-XL
- **Languages**: 12 PLs x 23 natural languages
- **Parallel?**: Yes — same problems across NL-PL pairs
- **Task**: Cross-lingual code generation (NL prompt diversity)
- **Links**: [Paper](https://arxiv.org/abs/2402.16694), [GitHub](https://github.com/floatai/HumanEval-XL)

### AutoCodeBench (Tencent, 2025)
- **Languages**: 20 PLs including Python, Java, JavaScript, C++, Rust, Go
- **Parallel?**: Yes — problems parallel across languages
- **Task**: Code generation (>60% hard difficulty)
- **Links**: [Paper](https://arxiv.org/abs/2508.09101), [Website](https://autocodebench.github.io/), [GitHub](https://github.com/Tencent-Hunyuan/AutoCodeBenchmark)

### XLCoST
- **Languages**: 7 PLs — C++, Java, Python, C#, JavaScript, PHP, C
- **Parallel?**: Yes — fine-grained parallel data at snippet and program level
- **Task**: Code translation, summarization, synthesis, code search
- **Links**: [Paper](https://arxiv.org/abs/2206.08474), [HuggingFace](https://huggingface.co/datasets/codeparrot/xlcost-text-to-code)

### AVATAR
- **Languages**: Java, Python only
- **Parallel?**: Yes — 9,515 parallel Java-Python function pairs, 250 with unit tests
- **Task**: Code translation (Java <-> Python)
- **Notes**: Key dataset for Python-Java scaling path from synthetic tasks.
- **Links**: [Paper](https://arxiv.org/abs/2108.11590), [GitHub](https://github.com/wasiahmad/AVATAR)

### CodeTransOcean
- **Languages**: 45 PLs; core pairs include Java-Python
- **Parallel?**: Yes — includes parallel translation pairs
- **Task**: Code translation (multilingual + cross-framework)
- **Links**: [Paper](https://openreview.net/pdf?id=hv3VpXDIh8)

### Rust-Specific Benchmarks

**CRUST-Bench**: 100 C repos with manually-written safe Rust interfaces. Best models achieve 32-48%. [Paper](https://arxiv.org/abs/2504.15254)

**RustRepoTrans**: C/Java/Python -> Rust repo-level translation. Pass@1 around 29-32%. [Paper](https://arxiv.org/html/2411.13990v1)

**RustEvo^2**: 588 Rust API change tasks. [Paper](https://arxiv.org/abs/2503.16922)

## Language Coverage Across Benchmarks

| Language | Parallel benchmarks |
|----------|-------------------|
| Python | All |
| Java | MultiPL-E, HumanEval-X, MBXP, AutoCodeBench, CRUXEval-X, XLCoST, AVATAR |
| JavaScript | MultiPL-E, HumanEval-X, MBXP, AutoCodeBench, CRUXEval-X, XLCoST |
| Rust | MultiPL-E, AutoCodeBench, CRUXEval-X, McEval, CRUST-Bench |
| C++ | MultiPL-E, HumanEval-X, MBXP, AutoCodeBench, CRUXEval-X, XLCoST |
| Go | MultiPL-E, HumanEval-X, MBXP, AutoCodeBench, CRUXEval-X |

## Key Takeaways

- **Python+Java** is the most common parallel pair across datasets, with AVATAR (9.5K pairs) and XLCoST providing the best scaling path from synthetic to real-world tasks
- **Rust** appears in fewer but increasingly important benchmarks; models still struggle significantly with Rust (30-48% pass rates), making it a compelling research target
- **CRUXEval-X** is the most directly relevant benchmark to genfxn — it tests code reasoning (I/O prediction) rather than generation, across 19 parallel languages including both Java and Rust
- Most parallel benchmarks auto-transpile from Python, meaning they test "Python-style" problems in other syntax rather than idiomatic code per language. McEval is the exception but is not parallel.
- The gap: no existing benchmark offers controllable difficulty with parallel multi-language problems — this is what genfxn could uniquely provide
