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

    for i, rule in enumerate(spec.rules):
        cond = render_string_predicate_rust(rule.predicate, var)
        result = render_string_transform_rust(rule.transform, var)
        keyword = "if" if i == 0 else "} else if"
        lines.append(f"    {keyword} {cond} {{")
        lines.append(f"        {result}")

    default_result = render_string_transform_rust(spec.default_transform, var)
    if spec.rules:
        lines.append("    } else {")
        lines.append(f"        {default_result}")
        lines.append("    }")
    else:
        lines.append(f"    {default_result}")

    lines.append("}")
    return "\n".join(lines)
