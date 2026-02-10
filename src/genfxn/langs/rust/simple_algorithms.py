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

_I32_HELPERS = [
    "    fn i32_wrap(value: i64) -> i64 {",
    "        (value as i32) as i64",
    "    }",
    "    fn i32_add(lhs: i64, rhs: i64) -> i64 {",
    "        ((lhs as i32).wrapping_add(rhs as i32)) as i64",
    "    }",
    "    fn i32_sub(lhs: i64, rhs: i64) -> i64 {",
    "        ((lhs as i32).wrapping_sub(rhs as i32)) as i64",
    "    }",
    "    fn i32_mul(lhs: i64, rhs: i64) -> i64 {",
    "        ((lhs as i32).wrapping_mul(rhs as i32)) as i64",
    "    }",
    "    fn i32_neg(value: i64) -> i64 {",
    "        (value as i32).wrapping_neg() as i64",
    "    }",
    "    fn i32_abs(value: i64) -> i64 {",
    "        (value as i32).wrapping_abs() as i64",
    "    }",
    "    fn i32_clip(value: i64, low: i64, high: i64) -> i64 {",
    "        let value_i32 = value as i32;",
    "        let low_i32 = low as i32;",
    "        let high_i32 = high as i32;",
    "        low_i32.max(high_i32.min(value_i32)) as i64",
    "    }",
]


def _render_preprocess_rust(
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec, var: str
) -> list[str]:
    lines: list[str] = []
    if spec.pre_filter is not None:
        cond = render_predicate_rust(
            spec.pre_filter, "x", int32_wrap=True
        )
        lines.extend(
            [
                f"    let _filtered: Vec<i64> = {var}.iter().copied()"
                f".filter(|&x| {cond}).collect();",
                f"    let {var} = _filtered.as_slice();",
            ]
        )
    if spec.pre_transform is not None:
        expr = render_transform_rust(
            spec.pre_transform, "x", int32_wrap=True
        )
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

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            "    use std::collections::HashMap;",
            *_I32_HELPERS,
            f"    let _wrapped: Vec<i64> = {var}.iter().copied()"
            ".map(i32_wrap).collect();",
            f"    let {var} = _wrapped.as_slice();",
            *preprocess,
            f"    if {var}.is_empty() {{",
            f"        return i32_wrap({spec.empty_default});",
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
            lines.append(f"        return i32_wrap({spec.tie_default});")
            lines.append("    }")
        lines.append("    i32_wrap(*candidates.iter().min().unwrap())")
        lines.append("}")
    else:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            "    use std::collections::HashMap;",
            "    use std::collections::HashSet;",
            *_I32_HELPERS,
            f"    let _wrapped: Vec<i64> = {var}.iter().copied()"
            ".map(i32_wrap).collect();",
            f"    let {var} = _wrapped.as_slice();",
            *preprocess,
            f"    if {var}.is_empty() {{",
            f"        return i32_wrap({spec.empty_default});",
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
            lines.append(f"        return i32_wrap({spec.tie_default});")
            lines.append("    }")
        lines.extend(
            [
                f"    for &x in {var} {{",
                "        if candidates.contains(&x) {",
                "            return i32_wrap(x);",
                "        }",
                "    }",
                f"    i32_wrap({spec.empty_default})",
                "}",
            ]
        )
    return "\n".join(lines)


def _render_count_pairs_sum(
    spec: CountPairsSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_rust(spec, var)
    target = (spec.target + (1 << 31)) % (1 << 32) - (1 << 31)

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            *_I32_HELPERS,
            f"    let _wrapped: Vec<i64> = {var}.iter().copied()"
            ".map(i32_wrap).collect();",
            f"    let {var} = _wrapped.as_slice();",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if {var}.len() < 2 {{")
            lines.append(
                f"        return i32_wrap({spec.short_list_default});"
            )
            lines.append("    }")
        lines.extend(
            [
                "    let mut count: i64 = 0;",
                f"    for i in 0..{var}.len() {{",
                f"        for j in (i + 1)..{var}.len() {{",
                f"            if i32_add({var}[i], {var}[j]) == {target} {{",
                "                count = i32_add(count, 1);",
                "            }",
                "        }",
                "    }",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if count == 0 {")
            lines.append(f"        return i32_wrap({spec.no_result_default});")
            lines.append("    }")
        lines.append("    i32_wrap(count)")
        lines.append("}")
    else:
        lines = [
            f"fn {func_name}({var}: &[i64]) -> i64 {{",
            "    use std::collections::HashSet;",
            *_I32_HELPERS,
            f"    let _wrapped: Vec<i64> = {var}.iter().copied()"
            ".map(i32_wrap).collect();",
            f"    let {var} = _wrapped.as_slice();",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if {var}.len() < 2 {{")
            lines.append(
                f"        return i32_wrap({spec.short_list_default});"
            )
            lines.append("    }")
        lines.extend(
            [
                "    let mut seen_pairs: HashSet<(i64, i64)> = HashSet::new();",
                f"    for i in 0..{var}.len() {{",
                f"        for j in (i + 1)..{var}.len() {{",
                f"            if i32_add({var}[i], {var}[j]) == {target} {{",
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
            lines.append(f"        return i32_wrap({spec.no_result_default});")
            lines.append("    }")
        lines.append("    i32_wrap(seen_pairs.len() as i64)")
        lines.append("}")
    return "\n".join(lines)


def _render_max_window_sum(
    spec: MaxWindowSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_rust(spec, var)

    lines = [
        f"fn {func_name}({var}: &[i64]) -> i64 {{",
        *_I32_HELPERS,
        f"    let _wrapped: Vec<i64> = {var}.iter().copied().map(i32_wrap)"
        ".collect();",
        f"    let {var} = _wrapped.as_slice();",
        *preprocess,
    ]
    if spec.empty_default is not None:
        lines.append(f"    if {var}.is_empty() {{")
        lines.append(f"        return i32_wrap({spec.empty_default});")
        lines.append("    }")
    lines.extend(
        [
            f"    if {var}.len() < {spec.k} {{",
            f"        return i32_wrap({spec.invalid_k_default});",
            "    }",
            "    let mut window_sum: i64 = i32_wrap(0);",
            f"    for i in 0..{spec.k} {{",
            f"        window_sum = i32_add(window_sum, {var}[i]);",
            "    }",
            "    let mut max_sum = window_sum;",
            f"    for i in {spec.k}..{var}.len() {{",
            "        window_sum = i32_add("
            f"i32_sub(window_sum, {var}[i - {spec.k}]), {var}[i]);",
            "        max_sum = max_sum.max(window_sum);",
            "    }",
            "    i32_wrap(max_sum)",
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
