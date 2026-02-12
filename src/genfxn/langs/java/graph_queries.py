from genfxn.graph_queries.models import GraphQueriesSpec
from genfxn.langs.java._helpers import java_long_literal


def render_graph_queries(
    spec: GraphQueriesSpec,
    func_name: str = "f",
    src_var: str = "src",
    dst_var: str = "dst",
) -> str:
    lines = [
        f"public static long {func_name}(int {src_var}, int {dst_var}) {{",
        f"    int nNodes = {spec.n_nodes};",
        f"    boolean directed = {str(spec.directed).lower()};",
        f"    boolean weighted = {str(spec.weighted).lower()};",
        f'    String queryType = "{spec.query_type.value}";',
        "    long[][] edges = new long[][] {",
    ]

    for edge in spec.edges:
        lines.append(
            "        new long[] "
            + "{"
            + f"{java_long_literal(edge.u)}, "
            + f"{java_long_literal(edge.v)}, "
            + f"{java_long_literal(edge.w)}"
            + "},"
        )

    lines.extend(
        [
            "    };",
            "",
            f"    if ({src_var} < 0 || {src_var} >= nNodes) {{",
            "        throw new IllegalArgumentException(",
            f'            "src out of range: " + {src_var}',
            "        );",
            "    }",
            f"    if ({dst_var} < 0 || {dst_var} >= nNodes) {{",
            "        throw new IllegalArgumentException(",
            f'            "dst out of range: " + {dst_var}',
            "        );",
            "    }",
            "",
            f"    if ({src_var} == {dst_var}) {{",
            '        if (queryType.equals("reachable")) {',
            "            return 1;",
            "        }",
            "        return 0;",
            "    }",
            "",
            "    java.util.HashMap<Long, Long> best = "
            "new java.util.HashMap<>();",
            "    for (long[] edge : edges) {",
            "        long rawULong = edge[0];",
            "        long rawVLong = edge[1];",
            "        long rawW = edge[2];",
            "        if (rawULong < 0 || rawULong >= nNodes || "
            "rawVLong < 0 || rawVLong >= nNodes) {",
            "            throw new IllegalArgumentException(",
            '                "edge endpoint out of range for n_nodes=" + '
            "nNodes",
            "            );",
            "        }",
            "        int rawU = (int) rawULong;",
            "        int rawV = (int) rawVLong;",
            "        long weight = weighted ? rawW : 1L;",
            "        long key = (((long) rawU) << 32) ^ "
            "(rawV & 0xFFFF_FFFFL);",
            "        Long prev = best.get(key);",
            "        if (prev == null || weight < prev) {",
            "            best.put(key, weight);",
            "        }",
            "        if (!directed) {",
            "            long revKey = (((long) rawV) << 32) ^ "
            "(rawU & 0xFFFF_FFFFL);",
            "            Long revPrev = best.get(revKey);",
            "            if (revPrev == null || weight < revPrev) {",
                "                best.put(revKey, weight);",
            "            }",
            "        }",
            "    }",
            "",
            "    java.util.ArrayList<long[]>[] adjacency = "
            "new java.util.ArrayList[nNodes];",
            "    for (int node = 0; node < nNodes; node++) {",
            "        adjacency[node] = new java.util.ArrayList<>();",
            "    }",
            "    for (java.util.Map.Entry<Long, Long> entry : "
            "best.entrySet()) {",
            "        long key = entry.getKey();",
            "        int u = (int) (key >> 32);",
            "        int v = (int) key;",
            "        adjacency[u].add(new long[] {v, entry.getValue()});",
            "    }",
            "    for (java.util.ArrayList<long[]> neighbors : adjacency) {",
            "        neighbors.sort((left, right) -> {",
            "            int nodeCmp = Long.compare(left[0], right[0]);",
            "            if (nodeCmp != 0) {",
            "                return nodeCmp;",
            "            }",
            "            return Long.compare(left[1], right[1]);",
            "        });",
            "    }",
            "",
            '    if (queryType.equals("reachable")) {',
            "        java.util.HashSet<Integer> visited = "
            "new java.util.HashSet<>();",
            "        java.util.ArrayDeque<Integer> queue = "
            "new java.util.ArrayDeque<>();",
            f"        visited.add({src_var});",
            f"        queue.add({src_var});",
            "        while (!queue.isEmpty()) {",
            "            int node = queue.removeFirst();",
            f"            if (node == {dst_var}) {{",
            "                return 1;",
            "            }",
            "            for (long[] pair : adjacency[node]) {",
            "                int neighbor = (int) pair[0];",
            "                if (visited.contains(neighbor)) {",
                "                    continue;",
                "                }",
            "                visited.add(neighbor);",
            "                queue.addLast(neighbor);",
            "            }",
            "        }",
            "        return 0;",
            "    }",
            "",
            '    if (queryType.equals("min_hops")) {',
            "        java.util.HashSet<Integer> visited = "
            "new java.util.HashSet<>();",
            "        java.util.ArrayDeque<int[]> queue = "
            "new java.util.ArrayDeque<>();",
            f"        visited.add({src_var});",
            f"        queue.add(new int[] {{{src_var}, 0}});",
            "        while (!queue.isEmpty()) {",
            "            int[] item = queue.removeFirst();",
            "            int node = item[0];",
            "            int hops = item[1];",
            f"            if (node == {dst_var}) {{",
            "                return hops;",
            "            }",
            "            for (long[] pair : adjacency[node]) {",
            "                int neighbor = (int) pair[0];",
            "                if (visited.contains(neighbor)) {",
                "                    continue;",
                "                }",
            "                visited.add(neighbor);",
            "                queue.addLast(new int[] {neighbor, hops + 1});",
            "            }",
            "        }",
            "        return -1;",
            "    }",
            "",
            "    java.util.HashMap<Integer, Long> bestCostPrev = "
            "new java.util.HashMap<>();",
            f"    bestCostPrev.put({src_var}, 0L);",
            "    for (int iter = 0; iter < nNodes - 1; iter++) {",
            "        boolean changed = false;",
            "        java.util.HashMap<Integer, Long> bestCostCurr = "
            "new java.util.HashMap<>(bestCostPrev);",
            "        for (int node = 0; node < nNodes; node++) {",
            "            Long cost = bestCostPrev.get(node);",
            "            if (cost == null) {",
            "                continue;",
            "            }",
            "            for (long[] pair : adjacency[node]) {",
            "                int neighbor = (int) pair[0];",
            "                long weight = pair[1];",
            "                long nextCost = "
            "(cost > Long.MAX_VALUE - weight) "
            "? Long.MAX_VALUE : cost + weight;",
            "                Long prev = bestCostCurr.get(neighbor);",
            "                if (prev != null && nextCost >= prev) {",
            "                    continue;",
            "                }",
            "                bestCostCurr.put(neighbor, nextCost);",
            "                changed = true;",
            "            }",
            "        }",
            "        bestCostPrev = bestCostCurr;",
            "        if (!changed) {",
            "            break;",
            "        }",
            "    }",
            f"    Long result = bestCostPrev.get({dst_var});",
            "    if (result == null) {",
            "        return -1L;",
            "    }",
            "    return result;",
            "}",
        ]
    )
    return "\n".join(lines)
