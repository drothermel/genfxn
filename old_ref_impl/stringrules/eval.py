from genfxn.core.string_predicates import eval_string_predicate
from genfxn.core.string_transforms import eval_string_transform
from genfxn.stringrules.models import StringRulesSpec


def eval_stringrules(spec: StringRulesSpec, s: str) -> str:
    """Evaluate string rules with first-match-wins semantics."""
    for rule in spec.rules:
        if eval_string_predicate(rule.predicate, s):
            return eval_string_transform(rule.transform, s)
    return eval_string_transform(spec.default_transform, s)
