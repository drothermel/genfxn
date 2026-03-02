from genfxn.core.string_predicates import render_string_predicate
from genfxn.core.string_transforms import render_string_transform
from genfxn.stringrules.models import StringRulesSpec


def render_stringrules(
    spec: StringRulesSpec, func_name: str = "f", var: str = "s"
) -> str:
    """Render string rules as an if/elif chain."""
    lines = [f"def {func_name}({var}: str) -> str:"]

    for i, rule in enumerate(spec.rules):
        cond = render_string_predicate(rule.predicate, var)
        result = render_string_transform(rule.transform, var)
        keyword = "if" if i == 0 else "elif"
        lines.append(f"    {keyword} {cond}:")
        lines.append(f"        return {result}")

    # Default case
    default_result = render_string_transform(spec.default_transform, var)
    if spec.rules:
        lines.append("    else:")
        lines.append(f"        return {default_result}")
    else:
        lines.append(f"    return {default_result}")

    return "\n".join(lines)
