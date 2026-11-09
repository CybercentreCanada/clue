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


def test_builtin_metadata_preserves_case_settings_and_priorities():
    assert CASE_INSENSITIVE_TYPES == ["ip", "domain", "port", "tenant_id", "mac_address"]
    for type_name, definition in SUPPORTED_TYPES.items():
        assert definition["case_sensitive"] == (type_name not in CASE_INSENSITIVE_TYPES)
        assert definition.get("priority", 0) == (10 if type_name in {"ipv4", "ipv6"} else 0)
        assert definition["regex"] is None or isinstance(definition["regex"], str)


def test_registration_preserves_positional_arguments_and_adds_priority():
    add_supported_type("ticket", r"^ticket-\d+$", "extension", True, 100)
    assert SUPPORTED_TYPES["extension_ticket"] == {
        "regex": r"^ticket-\d+$",
        "case_sensitive": False,
        "priority": 100,
    }
    assert "extension_ticket" in CASE_INSENSITIVE_TYPES
    assert Selector(type="extension_ticket", value="TICKET-123").value == "ticket-123"


def test_registration_defaults():
    add_supported_type("custom")
    assert SUPPORTED_TYPES["custom"] == {"regex": None, "case_sensitive": True, "priority": 0}


def test_registration_accepts_negative_priority():
    add_supported_type("fallback", r".*", priority=-10)
    assert SUPPORTED_TYPES["fallback"]["priority"] == -10


def test_reregistration_preserves_order_and_synchronizes_case_settings():
    add_supported_type("custom", case_insensitive=True)
    add_supported_type("later")
    original_order = list(SUPPORTED_TYPES)
    add_supported_type("custom", case_insensitive=True)
    assert CASE_INSENSITIVE_TYPES.count("custom") == 1
    add_supported_type("custom", case_insensitive=False, priority=5)
    assert "custom" not in CASE_INSENSITIVE_TYPES
    assert SUPPORTED_TYPES["custom"]["case_sensitive"] is True
    assert list(SUPPORTED_TYPES) == original_order


@pytest.mark.parametrize(
    "type_name,value,expected",
    [
        ("domain", "EXAMPLE.COM", "example.com"),
        ("mac_address", "AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff"),
        ("email_path", "USER_EMAIL://MixedCase", "USER_EMAIL://MixedCase"),
        ("ipv6", "2001:DB8::1", "2001:DB8::1"),
        ("custom_unknown", "MixedCase", "MixedCase"),
    ],
)
def test_selector_normalization_is_unchanged(type_name, value, expected):
    assert Selector(type=type_name, value=value).value == expected
