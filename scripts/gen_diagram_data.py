"""Generate class diagram data from src/genfxn source code.

Parses Python AST to extract classes, inheritance, field composition,
imports (uses), and registry relationships. Outputs JSON consumed by
the React Flow diagram app.

Usage:
    uv run python scripts/gen_diagram_data.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

SRC_ROOT = Path(__file__).parent.parent / "src" / "genfxn"
OUT_PATH = (
    Path(__file__).parent.parent
    / "tools"
    / "class-diagram"
    / "src"
    / "data"
    / "diagram.json"
)

# Bases to ignore for inheritance edges
IGNORE_BASES = {"BaseModel", "ABC", "Protocol", "object"}

# Type names to ignore in annotation references
IGNORE_TYPE_REFS = {"Any", "None", "Literal", "Field", "Callable", "Optional", "Union"}


# ── AST helpers ──────────────────────────────────────────────────────


def _base_names(node: ast.ClassDef) -> list[str]:
    names = []
    for b in node.bases:
        if isinstance(b, ast.Name):
            names.append(b.id)
        elif isinstance(b, ast.Attribute):
            names.append(b.attr)
    return names


def _fields(node: ast.ClassDef) -> list[dict[str, str]]:
    out = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            name = item.target.id
            if name.startswith("_") or name == "model_config":
                continue
            out.append({"name": name, "type": ast.unparse(item.annotation)})
    return out


def _is_protocol(node: ast.ClassDef) -> bool:
    for b in node.bases:
        if isinstance(b, ast.Name) and b.id == "Protocol":
            return True
    return False


def _type_refs(type_str: str) -> list[str]:
    """Extract PascalCase identifiers from a type annotation string."""
    refs = re.findall(r"\b([A-Z][A-Za-z0-9]+)\b", type_str)
    return [r for r in refs if r not in IGNORE_TYPE_REFS]


def _registry_dicts(tree: ast.Module) -> list[tuple[str, list[str]]]:
    """Find module-level dict assignments ending in REGISTRY."""
    results = []
    for node in ast.iter_child_nodes(tree):
        # Handle both `X = {...}` and `X: type = {...}`
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            value = node.value
        else:
            continue
        if not name.endswith("REGISTRY"):
            continue
        if not isinstance(value, ast.Dict):
            continue
        values = []
        for v in value.values:
            if isinstance(v, ast.Name):
                values.append(v.id)
            elif isinstance(v, ast.Starred) and isinstance(v.value, ast.Name):
                values.append(v.value.id)
        results.append((name, values))
    return results


def _imports(tree: ast.Module) -> list[tuple[str, str]]:
    """Extract (module_path, name) from 'from genfxn.x import Y'."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("genfxn"):
            for alias in node.names:
                out.append((node.module, alias.name))
    return out


def _public_functions(tree: ast.Module) -> list[str]:
    return [
        n.name
        for n in ast.iter_child_nodes(tree)
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
    ]


# ── Kind classification ──────────────────────────────────────────────


FOUNDATIONAL_SPACES = {"CategoricalSpace", "ConstantSpace", "OrdinalSpace"}


def _classify(name: str, bases: list[str], is_proto: bool) -> str | None:
    if is_proto:
        return "protocol"
    if "ABC" in bases:
        if name in FOUNDATIONAL_SPACES:
            return "space-foundational"
        return "abstract"
    if "Space" in name:
        if name in FOUNDATIONAL_SPACES:
            return "space-foundational"
        if any(b in ("CategoricalSpace", "StringSpace") for b in bases):
            return "space-leaf"
        return "space"
    if "Op" in name:
        if any(b == "BaseOp" for b in bases):
            return "op-leaf"
        return "op"
    return None


def _badge(kind: str, bases: list[str]) -> str:
    if kind == "protocol":
        return "Protocol"
    if kind == "abstract":
        return "ABC"
    if kind in ("op", "op-leaf"):
        if "CompoundOp" in bases:
            return "CompoundOp"
        return "Op"
    if kind == "space-foundational":
        return "Core"
    if kind in ("space", "space-leaf"):
        return "Space"
    return kind


def _width(name: str, fields: list[dict[str, str]]) -> int:
    lengths = [len(name) + 4]
    for f in fields:
        lengths.append(len(f["name"]) + len(f["type"]) + 2)
    return max(150, min(300, max(lengths) * 8 + 40))


# ── Main ─────────────────────────────────────────────────────────────


def collect_data() -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen: set[str] = set()

    # Maps for cross-referencing
    class_files: dict[str, str] = {}  # class_name -> rel_path
    registries: dict[str, dict[str, Any]] = {}  # REGISTRY_NAME -> {file, values}
    file_imports: dict[str, list[tuple[str, str]]] = {}  # rel_path -> [(mod, name)]

    py_files = sorted(SRC_ROOT.rglob("*.py"))

    # ── Pass 1: index everything ─────────────────────────────────
    for pf in py_files:
        rel = str(pf.relative_to(SRC_ROOT))
        if "__init__" in rel:
            continue
        try:
            tree = ast.parse(pf.read_text())
        except SyntaxError:
            continue

        file_imports[rel] = _imports(tree)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_files[node.name] = rel

        for reg_name, reg_values in _registry_dicts(tree):
            registries[reg_name] = {"file": rel, "values": reg_values}

    # ── Pass 2: build class nodes + edges ────────────────────────
    for pf in py_files:
        rel = str(pf.relative_to(SRC_ROOT))
        if "__init__" in rel:
            continue
        try:
            tree = ast.parse(pf.read_text())
        except SyntaxError:
            continue

        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            bases = _base_names(node)
            is_proto = _is_protocol(node)
            kind = _classify(node.name, bases, is_proto)
            if kind is None or node.name in seen:
                continue
            seen.add(node.name)

            fields = _fields(node)
            desc = ast.get_docstring(node) or ""

            nodes.append({
                "id": node.name,
                "kind": kind,
                "file": rel,
                "badge": _badge(kind, bases),
                "desc": desc,
                "fields": fields,
                "width": _width(node.name, fields),
            })

            # Inheritance
            for b in bases:
                if b not in IGNORE_BASES:
                    edges.append({"source": node.name, "target": b, "type": "inherits"})

            # Composition (field type annotations referencing known classes)
            field_refs: set[str] = set()
            for f in fields:
                for ref in _type_refs(f["type"]):
                    if ref in class_files and ref != node.name and ref not in bases:
                        field_refs.add(ref)
                        # Use specific edge types for op input_space and transform_space
                        if f["name"] == "input_space":
                            edge_type = "input_space"
                        elif f["name"] == "transform_space":
                            edge_type = "transform_space"
                        else:
                            edge_type = "composes"
                        edges.append({"source": node.name, "target": ref, "type": edge_type})

            # Uses (imports not already covered by inherits/composes)
            for _, imp_name in file_imports.get(rel, []):
                if imp_name in bases or imp_name in field_refs or imp_name == node.name:
                    continue
                if imp_name in seen or imp_name in class_files or imp_name in registries:
                    edge_type = "uses_registry" if imp_name in registries else "uses"
                    edges.append({"source": node.name, "target": imp_name, "type": edge_type})

    # ── Pass 3: helper/template modules (no classes, has functions) ──
    for pf in py_files:
        rel = str(pf.relative_to(SRC_ROOT))
        if "__init__" in rel:
            continue
        # Skip files that have classes (already handled) or registries
        if any(class_files.get(c) == rel for c in class_files):
            # Exception: types.py has both classes and type aliases
            if pf.stem != "types":
                continue
        # Skip registry files (handled separately)
        if any(r["file"] == rel for r in registries.values()):
            continue

        try:
            tree = ast.parse(pf.read_text())
        except SyntaxError:
            continue

        funcs = _public_functions(tree)
        # Also grab module-level StrEnum classes + type aliases for types.py
        extra_items: list[str] = []
        for n in ast.iter_child_nodes(tree):
            if isinstance(n, ast.ClassDef) and n.name not in seen:
                extra_items.append(n.name)
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and not t.id.startswith("_") and t.id[0].isupper():
                        extra_items.append(t.id)

        items = funcs + extra_items
        if not items:
            continue

        mod_name = pf.stem
        if mod_name in seen:
            continue
        seen.add(mod_name)

        kind = "types" if mod_name == "types" or (extra_items and not funcs) else "template"

        # Skip template/helper modules — not interesting for the diagram
        if kind == "template":
            continue

        badge = "Module"
        display_fields = [{"name": it, "type": ""} for it in items[:3]]
        if len(items) > 3:
            display_fields.append({"name": f"+{len(items) - 3} more", "type": ""})

        nodes.append({
            "id": mod_name,
            "kind": kind,
            "file": rel,
            "badge": badge,
            "desc": f"Module with {len(items)} exports.",
            "fields": display_fields,
            "width": 230,
        })

    # ── Pass 4: registry nodes + edges ───────────────────────────
    for reg_name, reg_info in registries.items():
        if reg_name in seen:
            continue
        seen.add(reg_name)

        nodes.append({
            "id": reg_name,
            "kind": "registry",
            "file": reg_info["file"],
            "badge": "Registry",
            "desc": f"Registry mapping op_type names to classes.",
            "fields": [],
            "width": 215,
        })

        for value in reg_info["values"]:
            if value in seen:
                edges.append({"source": reg_name, "target": value, "type": "registers"})

    # ── Deduplicate and filter edges ─────────────────────────────
    edge_keys: set[str] = set()
    unique: list[dict[str, str]] = []
    for e in edges:
        if e["source"] not in seen or e["target"] not in seen:
            continue
        key = f"{e['source']}-{e['target']}-{e['type']}"
        if key not in edge_keys:
            edge_keys.add(key)
            unique.append(e)

    return {"nodes": nodes, "edges": unique}


def main() -> None:
    data = collect_data()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n")
    n_nodes = len(data["nodes"])
    n_edges = len(data["edges"])
    print(f"Generated {n_nodes} nodes, {n_edges} edges → {OUT_PATH}")


if __name__ == "__main__":
    main()
