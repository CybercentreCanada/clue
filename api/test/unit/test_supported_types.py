import pytest

from clue.constants.supported_types import CASE_INSENSITIVE_TYPES, SUPPORTED_TYPES, add_supported_type
from clue.models.selector import Selector


@pytest.fixture(autouse=True)
def restore_registry():
    original_types = SUPPORTED_TYPES.copy()
    original_case_insensitive_types = CASE_INSENSITIVE_TYPES.copy()
    yield
    SUPPORTED_TYPES.clear()
    SUPPORTED_TYPES.update(original_types)
    CASE_INSENSITIVE_TYPES[:] = original_case_insensitive_types


def test_builtin_metadata_preserves_normalization_and_priorities():
    assert CASE_INSENSITIVE_TYPES == ["ip", "domain", "port", "tenant_id", "mac_address"]
    for type_name, definition in SUPPORTED_TYPES.items():
        assert definition["case_sensitive"] == (type_name not in CASE_INSENSITIVE_TYPES)
        assert definition.get("priority", 0) == (10 if type_name in {"ipv4", "ipv6"} else 0)
    assert list(SUPPORTED_TYPES).index("md5") < list(SUPPORTED_TYPES).index("ja3")


def test_extension_registration_metadata_and_stable_order():
    add_supported_type("ticket", r"^ticket-\d+$", "extension", False, 100)
    assert SUPPORTED_TYPES["extension_ticket"] == {
        "regex": r"^ticket-\d+$",
        "case_sensitive": True,
        "priority": 100,
    }
    assert Selector(type="extension_ticket", value="TICKET-123").value == "TICKET-123"
    original_order = list(SUPPORTED_TYPES)
    add_supported_type("ticket", r"^ticket-\d+$", "extension", True, -1)
    assert list(SUPPORTED_TYPES) == original_order
    assert CASE_INSENSITIVE_TYPES.count("extension_ticket") == 1
    assert Selector(type="extension_ticket", value="TICKET-123").value == "ticket-123"
    add_supported_type("ticket", namespace="extension")
    assert "extension_ticket" not in CASE_INSENSITIVE_TYPES
    assert SUPPORTED_TYPES["extension_ticket"] == {"regex": None, "case_sensitive": True, "priority": 0}


@pytest.mark.parametrize(
    "type_name,value",
    [("email_address", "Alice@EXAMPLE.COM"), ("url", "http://EXAMPLE.COM/MixedCase")],
)
def test_case_sensitive_selector_values_are_preserved(type_name, value):
    assert Selector(type=type_name, value=value).value == value
