from genfxn.langs.java._helpers import java_long_literal
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
    spec: MostFrequentSpec | CountPairsSumSpec | MaxWindowSumSpec,
    var: str,
) -> list[str]:
    lines: list[str] = []
    if spec.pre_filter is not None:
        cond = render_predicate_java(spec.pre_filter, "x")
        lines.extend(
            [
                f"    long[] _filtered = java.util.Arrays.stream({var})"
                f".filter(x -> {cond}).toArray();",
                f"    {var} = _filtered;",
            ]
        )
    if spec.pre_transform is not None:
        expr = render_transform_java(spec.pre_transform, "x")
        lines.extend(
            [
                f"    long[] _mapped = java.util.Arrays.stream({var})"
                f".map(x -> {expr}).toArray();",
                f"    {var} = _mapped;",
            ]
        )
    return lines


def _render_most_frequent(
    spec: MostFrequentSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    preprocess = _render_preprocess_java(spec, var)
    empty_default = java_long_literal(spec.empty_default)
    tie_default = (
        java_long_literal(spec.tie_default)
        if spec.tie_default is not None
        else None
    )

    if spec.tie_break == TieBreakMode.SMALLEST:
        lines = [
            f"public static long {func_name}(long[] {var}) {{",
            *preprocess,
            f"    if ({var}.length == 0) {{",
            f"        return {empty_default};",
            "    }",
            "    java.util.HashMap<Long, Long> counts = "
            "new java.util.HashMap<>();",
            f"    for (long x : {var}) {{",
            "        counts.put(x, counts.getOrDefault(x, 0L) + 1L);",
            "    }",
            (
                "    long max_count = "
                "java.util.Collections.max(counts.values());"
            ),
            "    java.util.ArrayList<Long> candidates = "
            "new java.util.ArrayList<>();",
            "    for (var entry : counts.entrySet()) {",
            "        if (entry.getValue() == max_count) {",
            "            candidates.add(entry.getKey());",
            "        }",
            "    }",
        ]
        if spec.tie_default is not None:
            lines.append("    if (candidates.size() > 1) {")
            assert tie_default is not None
            lines.append(f"        return {tie_default};")
            lines.append("    }")
        lines.append("    return java.util.Collections.min(candidates);")
        lines.append("}")
    else:
        lines = [
            f"public static long {func_name}(long[] {var}) {{",
            *preprocess,
            f"    if ({var}.length == 0) {{",
            f"        return {empty_default};",
            "    }",
            "    java.util.HashMap<Long, Long> counts = "
            "new java.util.HashMap<>();",
            f"    for (long x : {var}) {{",
            "        counts.put(x, counts.getOrDefault(x, 0L) + 1L);",
            "    }",
            (
                "    long max_count = "
                "java.util.Collections.max(counts.values());"
            ),
            "    java.util.HashSet<Long> candidates = "
            "new java.util.HashSet<>();",
            "    for (var entry : counts.entrySet()) {",
            "        if (entry.getValue() == max_count) {",
            "            candidates.add(entry.getKey());",
            "        }",
            "    }",
        ]
        if spec.tie_default is not None:
            lines.append("    if (candidates.size() > 1) {")
            assert tie_default is not None
            lines.append(f"        return {tie_default};")
            lines.append("    }")
        lines.extend(
            [
                f"    for (long x : {var}) {{",
                "        if (candidates.contains(x)) {",
                "            return x;",
                "        }",
                "    }",
                f"    return {empty_default};",
                "}",
            ]
        )
    return "\n".join(lines)


def _render_count_pairs_sum(
    spec: CountPairsSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    preprocess = _render_preprocess_java(spec, var)
    target = java_long_literal(spec.target)
    short_list_default = (
        java_long_literal(spec.short_list_default)
        if spec.short_list_default is not None
        else None
    )
    no_result_default = (
        java_long_literal(spec.no_result_default)
        if spec.no_result_default is not None
        else None
    )

    if spec.counting_mode == CountingMode.ALL_INDICES:
        lines = [
            f"public static long {func_name}(long[] {var}) {{",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if ({var}.length < 2) {{")
            assert short_list_default is not None
            lines.append(f"        return {short_list_default};")
            lines.append("    }")
        lines.extend(
            [
                "    long count = 0L;",
                f"    for (int i = 0; i < {var}.length; i++) {{",
                f"        for (int j = i + 1; j < {var}.length; j++) {{",
                f"            if ({var}[i] + {var}[j] == {target}) {{",
                "                count += 1L;",
                "            }",
                "        }",
                "    }",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if (count == 0L) {")
            assert no_result_default is not None
            lines.append(f"        return {no_result_default};")
            lines.append("    }")
        lines.append("    return count;")
        lines.append("}")
    else:
        lines = [
            f"public static long {func_name}(long[] {var}) {{",
            *preprocess,
        ]
        if spec.short_list_default is not None:
            lines.append(f"    if ({var}.length < 2) {{")
            assert short_list_default is not None
            lines.append(f"        return {short_list_default};")
            lines.append("    }")
        lines.extend(
            [
                "    java.util.HashSet<java.util.List<Long>> seen_pairs = "
                "new java.util.HashSet<>();",
                f"    for (int i = 0; i < {var}.length; i++) {{",
                f"        for (int j = i + 1; j < {var}.length; j++) {{",
                f"            if ({var}[i] + {var}[j] == {target}) {{",
                "                seen_pairs.add(",
                "                    java.util.List.of(",
                f"                        Math.min({var}[i], {var}[j]),",
                f"                        Math.max({var}[i], {var}[j])",
                "                    )",
                "                );",
                "            }",
                "        }",
                "    }",
            ]
        )
        if spec.no_result_default is not None:
            lines.append("    if (seen_pairs.isEmpty()) {")
            assert no_result_default is not None
            lines.append(f"        return {no_result_default};")
            lines.append("    }")
        lines.append("    return (long) seen_pairs.size();")
        lines.append("}")
    return "\n".join(lines)


def _render_max_window_sum(
    spec: MaxWindowSumSpec,
    func_name: str = "f",
    var: str = "xs",
) -> str:
    preprocess = _render_preprocess_java(spec, var)
    k = spec.k
    invalid_k_default = java_long_literal(spec.invalid_k_default)
    empty_default = (
        java_long_literal(spec.empty_default)
        if spec.empty_default is not None
        else None
    )

    lines = [
        f"public static long {func_name}(long[] {var}) {{",
        *preprocess,
    ]
    if spec.empty_default is not None:
        lines.append(f"    if ({var}.length == 0) {{")
        assert empty_default is not None
        lines.append(f"        return {empty_default};")
        lines.append("    }")
    lines.extend(
        [
            f"    if ({var}.length < {k}) {{",
            f"        return {invalid_k_default};",
            "    }",
            "    long window_sum = 0L;",
            f"    for (int i = 0; i < {k}; i++) {{",
            f"        window_sum += {var}[i];",
            "    }",
            "    long max_sum = window_sum;",
            f"    for (int i = {k}; i < {var}.length; i++) {{",
            f"        window_sum = window_sum - {var}[i - {k}] + {var}[i];",
            "        max_sum = Math.max(max_sum, window_sum);",
            "    }",
            "    return max_sum;",
            "}",
        ]
    )
    return "\n".join(lines)


def render_simple_algorithms(
    spec: SimpleAlgorithmsSpec,
    func_name: str = "f",
    var: str = "xs",
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
