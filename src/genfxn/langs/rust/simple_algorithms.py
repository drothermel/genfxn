from genfxn.langs.rust._helpers import rust_i64_literal
from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.langs.rust.transforms import render_transform_rust
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)


def _i64_expr(value: int) -> str:
    literal = rust_i64_literal(value)
    if literal.endswith("i64"):
        return literal[:-3]
    return literal


def _render_preprocess_rust(
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec, var: str
) -> list[str]:
    lines: list[str] = []
    if spec.pre_filter is not None:
        cond = render_predicate_rust(spec.pre_filter, "x")
        lines.extend(
            [
                f"    let _filtered: Vec<i64> = {var}.iter().copied()"
                f".filter(|&x| {cond}).collect();",
                f"    let {var} = _filtered.as_slice();",
            ]
        )
    if spec.pre_transform is not None:
        expr = render_transform_rust(spec.pre_transform, "x")
        lines.extend(
            [
                f"    let _mapped: Vec<i64> = {var}.iter().copied()"
                f".map(|x| {expr}).collect();",
                f"    let {var} = _mapped.as_slice();",
            ]
        )
    return lines


def _render_most_frequent(
    spec: MostFrequentSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_rust(spec, var)
    empty_default = _i64_expr(spec.empty_default)
    tie_default = (
        _i64_expr(spec.tie_default) if spec.tie_default is not None else None
    )

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            "    use std::collections::HashMap;",
            *preprocess,
            f"    if {var}.is_empty() {{",
            f"        return {empty_default};",
            "    }",
            "    let mut counts: HashMap<i64, i64> = HashMap::new();",
            f"    for &x in {var} {{",
            "        *counts.entry(x).or_insert(0) += 1;",
            "    }",
            "    let max_count = *counts.values().max().unwrap();",
            "    let mut candidates: Vec<i64> = Vec::new();",
            "    for (&k, &v) in &counts {",
            "        if v == max_count {",
            "            candidates.push(k);",
            "        }",
            "    }",
        ]
        if spec.tie_default is not None:
            lines.append("    if candidates.len() > 1 {")
            assert tie_default is not None
            lines.append(f"        return {tie_default};")
            lines.append("    }")
        lines.append("    *candidates.iter().min().unwrap()")
        lines.append("}")
    else:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            "    use std::collections::HashMap;",
            "    use std::collections::HashSet;",
            *preprocess,
            f"    if {var}.is_empty() {{",
            f"        return {empty_default};",
            "    }",
            "    let mut counts: HashMap<i64, i64> = HashMap::new();",
            f"    for &x in {var} {{",
            "        *counts.entry(x).or_insert(0) += 1;",
            "    }",
            "    let max_count = *counts.values().max().unwrap();",
            "    let mut candidates: HashSet<i64> = HashSet::new();",
            "    for (&k, &v) in &counts {",
            "        if v == max_count {",
            "            candidates.insert(k);",
            "        }",
            "    }",
        ]
        if spec.tie_default is not None:
            lines.append("    if candidates.len() > 1 {")
            assert tie_default is not None
            lines.append(f"        return {tie_default};")
            lines.append("    }")
        lines.extend(
            [
                f"    for &x in {var} {{",
                "        if candidates.contains(&x) {",
                "            return x;",
                "        }",
                "    }",
                f"    {empty_default}",
                "}",
            ]
        )
    return "\n".join(lines)


def _render_count_pairs_sum(
    spec: CountPairsSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_rust(spec, var)
    target = _i64_expr(spec.target)
    no_result_default = (
        _i64_expr(spec.no_result_default)
        if spec.no_result_default is not None
        else None
    )
    short_list_default = (
        _i64_expr(spec.short_list_default)
        if spec.short_list_default is not None
        else None
    )

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if {var}.len() < 2 {{")
            assert short_list_default is not None
            lines.append(f"        return {short_list_default};")
            lines.append("    }")
        lines.extend(
            [
                "    let mut count: i64 = 0;",
                f"    for i in 0..{var}.len() {{",
                f"        for j in (i + 1)..{var}.len() {{",
                f"            if {var}[i] + {var}[j] == {target} {{",
                "                count += 1;",
                "            }",
                "        }",
                "    }",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if count == 0 {")
            assert no_result_default is not None
            lines.append(f"        return {no_result_default};")
            lines.append("    }")
        lines.append("    count")
        lines.append("}")
    else:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            "    use std::collections::HashSet;",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if {var}.len() < 2 {{")
            assert short_list_default is not None
            lines.append(f"        return {short_list_default};")
            lines.append("    }")
        lines.extend(
            [
                "    let mut seen_pairs: HashSet<(i64, i64)> = HashSet::new();",
                f"    for i in 0..{var}.len() {{",
                f"        for j in (i + 1)..{var}.len() {{",
                f"            if {var}[i] + {var}[j] == {target} {{",
                "                seen_pairs.insert(("
                f"{var}[i].min({var}[j]), "
                f"{var}[i].max({var}[j])));",
                "            }",
                "        }",
                "    }",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if seen_pairs.is_empty() {")
            assert no_result_default is not None
            lines.append(f"        return {no_result_default};")
            lines.append("    }")
        lines.append("    seen_pairs.len() as i64")
        lines.append("}")
    return "\n".join(lines)


def _render_max_window_sum(
    spec: MaxWindowSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_rust(spec, var)
    invalid_k_default = _i64_expr(spec.invalid_k_default)
    empty_default = (
        _i64_expr(spec.empty_default)
        if spec.empty_default is not None
        else None
    )

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        *preprocess,
    ]
    if spec.empty_default is not None:
        lines.append(f"    if {var}.is_empty() {{")
        assert empty_default is not None
        lines.append(f"        return {empty_default};")
        lines.append("    }")
    lines.extend(
        [
            f"    if {var}.len() < {spec.k} {{",
            f"        return {invalid_k_default};",
            "    }",
            "    let mut window_sum: i64 = 0;",
            f"    for i in 0..{spec.k} {{",
            f"        window_sum += {var}[i];",
            "    }",
            "    let mut max_sum = window_sum;",
            f"    for i in {spec.k}..{var}.len() {{",
            (
                "        window_sum = window_sum "
                f"- {var}[i - {spec.k}] + {var}[i];"
            ),
            "        max_sum = max_sum.max(window_sum);",
            "    }",
            "    max_sum",
            "}",
        ]
    )
    return "\n".join(lines)


def render_simple_algorithms(
    spec: SimpleAlgorithmsSpec, func_name: str = "f", var: str = "xs"
) -> str:
    """Render a simple algorithms spec as a Rust function."""
    match spec:
        case MostFrequentSpec():
            return _render_most_frequent(spec, func_name, var)
        case CountPairsSumSpec():
            return _render_count_pairs_sum(spec, func_name, var)
        case MaxWindowSumSpec():
            return _render_max_window_sum(spec, func_name, var)
        case _:
            raise ValueError(f"Unknown simple algorithms spec: {spec}")
