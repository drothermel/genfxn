from genfxn.langs.java.predicates import render_predicate_java
from genfxn.langs.java.transforms import render_transform_java
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsSpec,
    TieBreakMode,
)


def _render_preprocess_java(
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec, var: str
) -> list[str]:
    lines: list[str] = []
    if spec.pre_filter is not None:
        cond = render_predicate_java(spec.pre_filter, "x")
        lines.extend([
            f"    int[] _filtered = java.util.Arrays.stream({var}).filter(x -> {cond}).toArray();",
            f"    {var} = _filtered;",
        ])
    if spec.pre_transform is not None:
        expr = render_transform_java(spec.pre_transform, "x")
        lines.extend([
            f"    int[] _mapped = java.util.Arrays.stream({var}).map(x -> {expr}).toArray();",
            f"    {var} = _mapped;",
        ])
    return lines


def _render_most_frequent(
    spec: MostFrequentSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_java(spec, var)

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            f"public static int {func_name}(int[] {var}) {{",
            *preprocess,
            f"    if ({var}.length == 0) {{",
            f"        return {spec.empty_default};",
            "    }",
            "    java.util.HashMap<Integer, Integer> counts = new java.util.HashMap<>();",
            f"    for (int x : {var}) {{",
            "        counts.put(x, counts.getOrDefault(x, 0) + 1);",
            "    }",
            "    int max_count = java.util.Collections.max(counts.values());",
            "    java.util.ArrayList<Integer> candidates = new java.util.ArrayList<>();",
            "    for (var entry : counts.entrySet()) {",
            "        if (entry.getValue() == max_count) {",
            "            candidates.add(entry.getKey());",
            "        }",
            "    }",
        ]
        if spec.tie_default is not None:
            lines.append("    if (candidates.size() > 1) {")
            lines.append(f"        return {spec.tie_default};")
            lines.append("    }")
        lines.append("    return java.util.Collections.min(candidates);")
        lines.append("}")
    else:
        lines = [
            f"public static int {func_name}(int[] {var}) {{",
            *preprocess,
            f"    if ({var}.length == 0) {{",
            f"        return {spec.empty_default};",
            "    }",
            "    java.util.HashMap<Integer, Integer> counts = new java.util.HashMap<>();",
            f"    for (int x : {var}) {{",
            "        counts.put(x, counts.getOrDefault(x, 0) + 1);",
            "    }",
            "    int max_count = java.util.Collections.max(counts.values());",
            "    java.util.HashSet<Integer> candidates = new java.util.HashSet<>();",
            "    for (var entry : counts.entrySet()) {",
            "        if (entry.getValue() == max_count) {",
            "            candidates.add(entry.getKey());",
            "        }",
            "    }",
        ]
        if spec.tie_default is not None:
            lines.append("    if (candidates.size() > 1) {")
            lines.append(f"        return {spec.tie_default};")
            lines.append("    }")
        lines.extend([
            f"    for (int x : {var}) {{",
            "        if (candidates.contains(x)) {",
            "            return x;",
            "        }",
            "    }",
            f"    return {spec.empty_default};",
            "}",
        ])
    return "\n".join(lines)


def _render_count_pairs_sum(
    spec: CountPairsSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_java(spec, var)

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            f"public static int {func_name}(int[] {var}) {{",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if ({var}.length < 2) {{")
            lines.append(f"        return {spec.short_list_default};")
            lines.append("    }")
        lines.extend([
            "    int count = 0;",
            f"    for (int i = 0; i < {var}.length; i++) {{",
            f"        for (int j = i + 1; j < {var}.length; j++) {{",
            f"            if ({var}[i] + {var}[j] == {spec.target}) {{",
            "                count += 1;",
            "            }",
            "        }",
            "    }",
        ])
        if spec.no_result_default is not None:
            lines.append("    if (count == 0) {")
            lines.append(f"        return {spec.no_result_default};")
            lines.append("    }")
        lines.append("    return count;")
        lines.append("}")
    else:
        lines = [
            f"public static int {func_name}(int[] {var}) {{",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if ({var}.length < 2) {{")
            lines.append(f"        return {spec.short_list_default};")
            lines.append("    }")
        lines.extend([
            "    java.util.HashSet<java.util.List<Integer>> seen_pairs = new java.util.HashSet<>();",
            f"    for (int i = 0; i < {var}.length; i++) {{",
            f"        for (int j = i + 1; j < {var}.length; j++) {{",
            f"            if ({var}[i] + {var}[j] == {spec.target}) {{",
            f"                seen_pairs.add(java.util.List.of(Math.min({var}[i], {var}[j]), Math.max({var}[i], {var}[j])));",
            "            }",
            "        }",
            "    }",
        ])
        if spec.no_result_default is not None:
            lines.append("    if (seen_pairs.isEmpty()) {")
            lines.append(f"        return {spec.no_result_default};")
            lines.append("    }")
        lines.append("    return seen_pairs.size();")
        lines.append("}")
    return "\n".join(lines)


def _render_max_window_sum(
    spec: MaxWindowSumSpec, func_name: str = "f", var: str = "xs"
) -> str:
    preprocess = _render_preprocess_java(spec, var)

    lines = [
        f"public static int {func_name}(int[] {var}) {{",
        *preprocess,
    ]
    if spec.empty_default is not None:
        lines.append(f"    if ({var}.length == 0) {{")
        lines.append(f"        return {spec.empty_default};")
        lines.append("    }")
    lines.extend([
        f"    if ({var}.length < {spec.k}) {{",
        f"        return {spec.invalid_k_default};",
        "    }",
        "    int window_sum = 0;",
        f"    for (int i = 0; i < {spec.k}; i++) {{",
        f"        window_sum += {var}[i];",
        "    }",
        "    int max_sum = window_sum;",
        f"    for (int i = {spec.k}; i < {var}.length; i++) {{",
        f"        window_sum = window_sum - {var}[i - {spec.k}] + {var}[i];",
        "        max_sum = Math.max(max_sum, window_sum);",
        "    }",
        "    return max_sum;",
        "}",
    ])
    return "\n".join(lines)


def render_simple_algorithms(
    spec: SimpleAlgorithmsSpec, func_name: str = "f", var: str = "xs"
) -> str:
    """Render a simple algorithms spec as a Java static method."""
    match spec:
        case MostFrequentSpec():
            return _render_most_frequent(spec, func_name, var)
        case CountPairsSumSpec():
            return _render_count_pairs_sum(spec, func_name, var)
        case MaxWindowSumSpec():
            return _render_max_window_sum(spec, func_name, var)
        case _:
            raise ValueError(f"Unknown simple algorithms spec: {spec}")
