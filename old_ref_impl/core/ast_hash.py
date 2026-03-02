from __future__ import annotations

import hashlib
from typing import Any

import srsly
import tree_sitter_java
import tree_sitter_python
import tree_sitter_rust
from tree_sitter import Language, Parser

from genfxn.core.codegen import _canonicalize_for_hash
from genfxn.langs.types import Language as GenfxnLanguage

AST_HASH_V1 = "ast_hash_v1"
_COMMENT_NODE_TYPES = frozenset({"comment", "line_comment", "block_comment"})


def _load_language(language_factory: Any) -> Any:
    raw = language_factory()
    if isinstance(raw, Language):
        return raw
    return Language(raw)


def _new_parser(language: Any) -> Parser:
    try:
        return Parser(language)
    except TypeError:
        parser = Parser()
        if hasattr(parser, "language"):
            parser.language = language
        else:  # pragma: no cover - compatibility fallback
            parser.set_language(language)
        return parser


_LANGUAGES: dict[str, Any] = {
    GenfxnLanguage.PYTHON.value: _load_language(tree_sitter_python.language),
    GenfxnLanguage.JAVA.value: _load_language(tree_sitter_java.language),
    GenfxnLanguage.RUST.value: _load_language(tree_sitter_rust.language),
}
_PARSERS: dict[str, Parser] = {
    name: _new_parser(language) for name, language in _LANGUAGES.items()
}


def _is_parse_successful(tree: Any) -> bool:
    root = tree.root_node
    return not bool(root.has_error)


def _parse(language: str, source: str) -> Any:
    parser = _PARSERS.get(language)
    if parser is None:
        supported = ", ".join(sorted(_PARSERS))
        raise ValueError(
            f"Unsupported AST language '{language}'. Supported: {supported}"
        )
    return parser.parse(source.encode("utf-8"))


def _extract_java_fallback_root(tree: Any) -> Any:
    root = tree.root_node
    for child in root.children:
        if child.type != "class_declaration":
            continue
        for class_child in child.children:
            if class_child.type != "class_body":
                continue
            named = [node for node in class_child.children if node.is_named]
            if len(named) == 1:
                return named[0]
            return class_child
    return root


def _serialize_node(node: Any, source_bytes: bytes) -> Any | None:
    if node.type in _COMMENT_NODE_TYPES:
        return None

    children: list[Any] = []
    for child in node.children:
        serialized_child = _serialize_node(child, source_bytes)
        if serialized_child is not None:
            children.append(serialized_child)

    if children:
        return {"children": children, "type": node.type}

    token = source_bytes[node.start_byte : node.end_byte].decode(
        "utf-8", errors="replace"
    )
    if not node.is_named:
        token = token.strip()
        if token == "":
            return None
    return {"token": token, "type": node.type}


def compute_ast_hash(language: str, code: str) -> str:
    tree = _parse(language, code)
    source = code
    root = tree.root_node

    if language == GenfxnLanguage.JAVA.value and not _is_parse_successful(tree):
        wrapped = (
            f"public final class __GenfxnTreeSitterWrapper__ {{\n{code}\n}}\n"
        )
        wrapped_tree = _parse(language, wrapped)
        if not _is_parse_successful(wrapped_tree):
            raise ValueError("tree-sitter parse failed for Java code")
        tree = wrapped_tree
        source = wrapped
        root = _extract_java_fallback_root(tree)
    elif not _is_parse_successful(tree):
        raise ValueError(f"tree-sitter parse failed for {language} code")

    serialized = _serialize_node(root, source.encode("utf-8"))
    if serialized is None:
        raise ValueError("Unable to serialize parsed AST")

    payload = {
        "ast": serialized,
        "language": language,
        "version": AST_HASH_V1,
    }
    canonical = srsly.json_dumps(
        _canonicalize_for_hash(payload), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_ast_id_map(code: str | dict[str, str]) -> dict[str, str]:
    if isinstance(code, str):
        return {GenfxnLanguage.PYTHON.value: compute_ast_hash("python", code)}

    ast_ids: dict[str, str] = {}
    for language, source in code.items():
        if not isinstance(source, str):
            raise ValueError(
                f"Code for language '{language}' must be a string source"
            )
        ast_ids[language] = compute_ast_hash(language, source)
    return ast_ids
