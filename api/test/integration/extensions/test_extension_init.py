import importlib
import logging
from pathlib import Path

import pytest
import werkzeug
from pydantic_settings import SettingsConfigDict

from clue.constants.supported_types import SUPPORTED_TYPES, add_supported_type
from clue.extensions.config import BaseExtensionConfig

# Workaround: Some tests or Flask extensions expect werkzeug.__version__ to be set to a valid string.
# In certain environments, this attribute may be missing or incorrect, causing import or compatibility errors.
# Setting it explicitly ensures consistent behavior during testing.
werkzeug.__version__ = "1.0.0"  # type: ignore


class ClueTestExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "test-extension.yml", yaml_file_encoding="utf-8", strict=True
    )


@pytest.fixture(autouse=True, scope="module")
def mock_plugin():
    from clue.extensions import EXTENSIONS

    conf = ClueTestExtensionConfig(name="test-extension")

    EXTENSIONS["test-extension"] = conf

    yield EXTENSIONS

    del EXTENSIONS["test-extension"]


def test_init_hook(caplog):
    """Test that the init hook is called when the app is loaded."""
    from clue.extensions import EXTENSIONS

    # Track if init was called
    init_called = {"called": False, "app": None}

    def mock_init(flask_app):
        init_called["called"] = True
        init_called["app"] = flask_app

    EXTENSIONS["test-extension"].modules.init = mock_init  # type: ignore[union-attr]

    with caplog.at_level(logging.INFO):
        app = importlib.import_module("clue.app")
        importlib.reload(app)

    assert init_called["called"], "Init function should have been called"
    assert init_called["app"] is not None, "Flask app should have been passed to init"


def test_init_can_add_supported_type(caplog):
    """Test that the init function can successfully call add_supported_type."""
    from clue.extensions import EXTENSIONS

    # Test type to add
    test_type = "test_custom_type"
    test_regex = r"^TEST-\d{5}$"

    # Remove test type if it exists from previous runs
    if test_type in SUPPORTED_TYPES:
        del SUPPORTED_TYPES[test_type]

    def mock_init_with_type_registration(flask_app):
        """Mock init function that registers a new supported type."""
        add_supported_type(test_type, test_regex)

    EXTENSIONS["test-extension"].modules.init = mock_init_with_type_registration  # type: ignore[union-attr]

    with caplog.at_level(logging.INFO):
        app = importlib.import_module("clue.app")
        importlib.reload(app)

    # Verify the type was added
    assert test_type in SUPPORTED_TYPES, f"Type '{test_type}' should have been added to SUPPORTED_TYPES"
    assert SUPPORTED_TYPES[test_type] == test_regex, f"Regex for '{test_type}' should match"

    # Verify logging
    assert f"Adding new type {test_type} to the default namespace with regex {test_regex}" in caplog.text

    # Cleanup
    del SUPPORTED_TYPES[test_type]


def test_init_can_add_namespaced_type(caplog):
    """Test that the init function can add types with custom namespaces."""
    from clue.extensions import EXTENSIONS

    # Test type with namespace
    test_type = "custom_id"
    test_namespace = "test-extension"
    test_regex = r"^\d{10}$"
    expected_key = f"{test_namespace}_{test_type}"

    # Remove test type if it exists from previous runs
    if expected_key in SUPPORTED_TYPES:
        del SUPPORTED_TYPES[expected_key]

    def mock_init_with_namespaced_type(flask_app):
        """Mock init function that registers a namespaced type."""
        add_supported_type(test_type, test_regex, namespace=test_namespace)

    EXTENSIONS["test-extension"].modules.init = mock_init_with_namespaced_type  # type: ignore[union-attr]

    with caplog.at_level(logging.INFO):
        app = importlib.import_module("clue.app")
        importlib.reload(app)

    # Verify the type was added with namespace
    assert expected_key in SUPPORTED_TYPES, f"Type '{expected_key}' should have been added to SUPPORTED_TYPES"
    assert SUPPORTED_TYPES[expected_key] == test_regex, f"Regex for '{expected_key}' should match"

    # Verify logging
    assert f"Adding type {test_type} to namespace {test_namespace} with regex {test_regex}" in caplog.text

    # Cleanup
    del SUPPORTED_TYPES[expected_key]


def test_init_can_add_multiple_types(caplog):
    """Test that the init function can add multiple types in one call."""
    from clue.extensions import EXTENSIONS

    # Multiple test types
    test_types = [
        ("ticket_id", r"^TICKET-\d{6}$", None),
        ("case_id", r"^CASE-\d{8}$", None),
        ("alert_id", r"^ALERT-[A-Z0-9]{12}$", "test-extension"),
    ]

    # Remove test types if they exist from previous runs
    for type_name, _, namespace in test_types:
        key = f"{namespace}_{type_name}" if namespace else type_name
        if key in SUPPORTED_TYPES:
            del SUPPORTED_TYPES[key]

    def mock_init_with_multiple_types(flask_app):
        """Mock init function that registers multiple types."""
        for type_name, regex, namespace in test_types:
            add_supported_type(type_name, regex, namespace=namespace)

    EXTENSIONS["test-extension"].modules.init = mock_init_with_multiple_types  # type: ignore[union-attr]

    with caplog.at_level(logging.INFO):
        app = importlib.import_module("clue.app")
        importlib.reload(app)

    # Verify all types were added
    for type_name, regex, namespace in test_types:
        key = f"{namespace}_{type_name}" if namespace else type_name
        assert key in SUPPORTED_TYPES, f"Type '{key}' should have been added to SUPPORTED_TYPES"
        assert SUPPORTED_TYPES[key] == regex, f"Regex for '{key}' should match"

    # Cleanup
    for type_name, _, namespace in test_types:
        key = f"{namespace}_{type_name}" if namespace else type_name
        del SUPPORTED_TYPES[key]
