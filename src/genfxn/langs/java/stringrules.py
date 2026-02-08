from genfxn.langs.java.string_predicates import render_string_predicate_java
from genfxn.langs.java.string_transforms import render_string_transform_java
from genfxn.stringrules.models import StringRulesSpec


def render_stringrules(
    spec: StringRulesSpec, func_name: str = "f", var: str = "s"
) -> str:
    """Render string rules as a Java static method."""
    lines = [f"public static String {func_name}(String {var}) {{"]

    for i, rule in enumerate(spec.rules):
        cond = render_string_predicate_java(rule.predicate, var)
        result = render_string_transform_java(rule.transform, var)
        keyword = "if" if i == 0 else "} else if"
        lines.append(f"    {keyword} ({cond}) {{")
        lines.append(f"        return {result};")

    default_result = render_string_transform_java(spec.default_transform, var)
    if spec.rules:
        lines.append("    } else {")
        lines.append(f"        return {default_result};")
        lines.append("    }")
    else:
        lines.append(f"    return {default_result};")

    lines.append("}")
    return "\n".join(lines)
