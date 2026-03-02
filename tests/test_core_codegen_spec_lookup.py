from genfxn.core.codegen import get_spec_value


def test_get_spec_value_simple_path() -> None:
    spec = {"template": "conditional_linear_sum"}
    assert get_spec_value(spec, "template") == "conditional_linear_sum"


def test_get_spec_value_nested_path() -> None:
    spec = {"predicate": {"kind": "even"}}
    assert get_spec_value(spec, "predicate.kind") == "even"


def test_get_spec_value_deeply_nested_path() -> None:
    spec = {"a": {"b": {"c": {"d": 42}}}}
    assert get_spec_value(spec, "a.b.c.d") == 42


def test_get_spec_value_list_index_path() -> None:
    spec = {
        "branches": [
            {"condition": {"kind": "lt"}},
            {"condition": {"kind": "ge"}},
        ]
    }
    assert get_spec_value(spec, "branches.0.condition.kind") == "lt"
    assert get_spec_value(spec, "branches.1.condition.kind") == "ge"


def test_get_spec_value_list_index_out_of_bounds() -> None:
    spec = {"branches": [{"kind": "lt"}]}
    assert get_spec_value(spec, "branches.5.kind") is None


def test_get_spec_value_missing_path() -> None:
    spec = {"predicate": {"kind": "even"}}
    assert get_spec_value(spec, "nonexistent") is None
    assert get_spec_value(spec, "predicate.nonexistent") is None
    assert get_spec_value(spec, "predicate.kind.extra") is None


def test_get_spec_value_empty_spec() -> None:
    assert get_spec_value({}, "anything") is None


def test_get_spec_value_non_dict_intermediate() -> None:
    spec = {"template": "value"}
    assert get_spec_value(spec, "template.nested") is None
