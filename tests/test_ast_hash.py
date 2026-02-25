from genfxn.core.ast_hash import compute_ast_hash, compute_ast_id_map


def test_python_ast_hash_formatting_invariant() -> None:
    code_a = "def f(x: int) -> int:\n    return x + 1\n"
    code_b = "def f( x:int)->int:\n\treturn x+1\n"
    assert compute_ast_hash("python", code_a) == compute_ast_hash(
        "python", code_b
    )


def test_python_ast_hash_changes_for_token_change() -> None:
    code_a = "def f(x: int) -> int:\n    return x + 1\n"
    code_b = "def f(x: int) -> int:\n    return x + 2\n"
    assert compute_ast_hash("python", code_a) != compute_ast_hash(
        "python", code_b
    )


def test_java_ast_hash_wrapper_fallback() -> None:
    java_method = "public static long f(long x) { return x + 1L; }"
    ast_hash = compute_ast_hash("java", java_method)
    assert isinstance(ast_hash, str)
    assert ast_hash


def test_java_ast_hash_formatting_invariant() -> None:
    code_a = "public final class S { static long f(long x) { return x + 1L; } }"
    code_b = (
        "public final class S {\n"
        "  static long f(long x){\n"
        "    return x+1L;\n"
        "  }\n"
        "}\n"
    )
    assert compute_ast_hash("java", code_a) == compute_ast_hash("java", code_b)


def test_java_ast_hash_changes_for_token_change() -> None:
    code_a = "public final class S { static long f(long x) { return x + 1L; } }"
    code_b = "public final class S { static long f(long x) { return x + 2L; } }"
    assert compute_ast_hash("java", code_a) != compute_ast_hash("java", code_b)


def test_rust_ast_hash_computes() -> None:
    rust_code = "pub fn f(x: i64) -> i64 { x + 1 }"
    ast_hash = compute_ast_hash("rust", rust_code)
    assert isinstance(ast_hash, str)
    assert ast_hash


def test_rust_ast_hash_formatting_invariant() -> None:
    code_a = "pub fn f(x: i64) -> i64 { x + 1 }"
    code_b = "pub fn f( x:i64 )->i64 {\n    x+1\n}\n"
    assert compute_ast_hash("rust", code_a) == compute_ast_hash("rust", code_b)


def test_rust_ast_hash_changes_for_token_change() -> None:
    code_a = "pub fn f(x: i64) -> i64 { x + 1 }"
    code_b = "pub fn f(x: i64) -> i64 { x + 2 }"
    assert compute_ast_hash("rust", code_a) != compute_ast_hash("rust", code_b)


def test_multi_language_ast_id_map() -> None:
    ast_id = compute_ast_id_map(
        {
            "python": "def f(x: int) -> int:\n    return x + 1\n",
            "java": "public static long f(long x) { return x + 1L; }",
            "rust": "pub fn f(x: i64) -> i64 { x + 1 }",
        }
    )
    assert set(ast_id) == {"python", "java", "rust"}
    assert all(isinstance(value, str) and value for value in ast_id.values())
