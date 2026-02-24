from genfxn.langs.rust.string_predicates import (
    render_python_isdigit_helper_rust,
    render_string_predicate_rust,
)
from genfxn.langs.rust.string_transforms import render_string_transform_rust
from genfxn.stringrules.models import StringRulesSpec


def render_stringrules(
    spec: StringRulesSpec, func_name: str = "f", var: str = "s"
) -> str:
    """Render string rules as a Rust function."""
    lines = [f"fn {func_name}({var}: &str) -> String {{"]
    lines.append(f"    {render_python_isdigit_helper_rust()}")

    default_result = render_string_transform_rust(spec.default_transform, var)
    if not spec.rules:
        lines.append(f"    {default_result}")
        lines.append("}")
        return "\n".join(lines)

    for rule in spec.rules:
        cond = render_string_predicate_rust(rule.predicate, var)
        result = render_string_transform_rust(rule.transform, var)
        lines.append(f"    if {cond} {{")
        lines.append(f"        return {result};")
        lines.append("    }")

    lines.append(f"    {default_result}")
    lines.append("}")

    return "\n".join(lines)
