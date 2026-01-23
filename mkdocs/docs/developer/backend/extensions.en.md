# Clue API Extensions

## Overview

Clue's extension system allows you to add custom functionality to the central API without modifying core code.
Extensions can register new API routes, add custom data types, integrate authentication mechanisms, and perform
initialization tasks when the application starts.

Extensions are loaded dynamically at startup based on the configuration and can seamlessly integrate with Clue's
existing infrastructure.

## Key Features

Extensions support the following capabilities:

- **Custom API Routes**: Add new API endpoints to extend Clue's functionality
- **Initialization Hooks**: Execute code during application startup
- **Authentication Integration**: Implement On-Behalf-Of (OBO) token exchange for external services
- **Custom Data Types**: Register new supported types with validation patterns
- **Feature Flags**: Control extension behavior through configurable features

## Extension Structure

### Basic Directory Layout

```
my-extension/
├── __init__.py
├── config.py              # Extension configuration
├── routes/                # Custom API routes (optional)
│   └── my_route.py
├── obo.py                 # OBO authentication module (optional)
└── extension.yml          # Extension configuration file
```

### Extension Configuration File

Extensions use a YAML configuration file to define their behavior and modules:

```yaml
name: "my-extension"

# Optional feature flags
features:
  enable_feature_x: true
  enable_feature_y: false

# Optional modules
modules:
  # Initialization function called on app startup
  init: "my_extension.init:initialize"

  # Custom API routes to register
  routes:
    - "my_route"  # Short form: will be prefixed with extension name
    # - "other_package.routes.custom_route"  # Full form: use as-is

  # OBO authentication module
  obo_module: true  # Short form: uses <extension>.obo:get_obo_token
  # obo_module: "my_extension.auth:custom_obo"  # Full form: custom path
```

### Extension Configuration Class

Create a `config.py` file in your extension:

```python
from pathlib import Path
from pydantic_settings import SettingsConfigDict
from clue.extensions.config import BaseExtensionConfig

class MyExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "extension.yml",
        yaml_file_encoding="utf-8",
        strict=True
    )

# Export the configuration instance
config = MyExtensionConfig(name="my-extension")
```

## Module Types

### 1. Initialization Module (init)

The initialization module is called once when the Flask application starts. This is useful for:

- Registering custom data types
- Setting up connections to external services
- Configuring extension-specific resources
- Performing one-time setup tasks

**Function Signature:**

```python
def initialize(flask_app) -> None:
    """
    Initialize the extension.

    Args:
        flask_app: The Flask application instance
    """
    pass
```

**Example:**

```python
# my_extension/init.py
from clue.constants.supported_types import add_supported_type
from clue.common.logging import get_logger

logger = get_logger(__file__)

def initialize(flask_app):
    """Initialize my extension."""
    logger.info("Initializing my-extension")

    # Register custom data types
    add_supported_type("ticket_id", r"^TICKET-\d{6}$")
    add_supported_type("custom_id", r"^\d{10}$", namespace="my-extension")

    # Perform other initialization
    logger.info("My extension initialized successfully")
```

### 2. Routes Module

Routes allow you to add custom API endpoints to Clue. Routes are Flask Blueprints that get registered with the main application.

**Example:**

```python
# my_extension/routes/my_route.py
from typing import Any
from clue.api import make_subapi_blueprint, ok
from clue.common.logging import get_logger

SUB_API = "myapi"
my_route = make_subapi_blueprint(SUB_API, api_version=1)
my_route._doc = "My Custom API"

logger = get_logger(__file__)

@my_route.route("/example", methods=["GET"])
def example_endpoint(**kwargs) -> tuple[dict[str, Any], int]:
    """
    Example endpoint.

    Returns:
        API response with success status
    """
    # Your custom logic here
    return ok({"message": "Hello from my extension!"})

@my_route.route("/process/<data_id>", methods=["POST"])
def process_endpoint(data_id: str, **kwargs) -> tuple[dict[str, Any], int]:
    """
    Process data by ID.

    Args:
        data_id: The ID of the data to process

    Returns:
        API response with processing results
    """
    # Your custom processing logic
    result = {"data_id": data_id, "status": "processed"}
    return ok(result)
```

The routes will be available at:
- `/api/v1/myapi/example`
- `/api/v1/myapi/process/<data_id>`

### 3. OBO Authentication Module

The On-Behalf-Of (OBO) module allows your extension to implement custom token exchange logic for accessing external
services on behalf of users.

**Function Signature:**

```python
def get_obo_token(service: str, access_token: str, user: str) -> str | None:
    """
    Exchange an access token for a service-specific OBO token.

    Args:
        service: The name of the service to get a token for
        access_token: The user's access token
        user: The username

    Returns:
        The OBO token for the service, or None if exchange fails
    """
    pass
```

**Example:**

```python
# my_extension/obo.py
import requests
from clue.common.logging import get_logger

logger = get_logger(__file__)

def get_obo_token(service: str, access_token: str, user: str) -> str | None:
    """Get an OBO token for the specified service."""
    try:
        if service == "my-external-service":
            # Implement your OBO token exchange logic
            response = requests.post(
                "https://auth.example.com/obo/token",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"user": user, "service": service}
            )

            if response.status_code == 200:
                return response.json()["access_token"]
            else:
                logger.error("OBO token exchange failed: %s", response.text)
                return None

        # Let other extensions or core handle other services
        return None

    except Exception as e:
        logger.exception("Exception during OBO token exchange for %s: %s", service, e)
        return None
```

## Registering Custom Data Types

Extensions can register custom data types that Clue will recognize and validate. This is typically done in the initialization module.

### Using add_supported_type

```python
from clue.constants.supported_types import add_supported_type

# Add a type to the default namespace
add_supported_type("email", r"^[\w\.-]+@[\w\.-]+\.\w+$")

# Add a type with a custom namespace
add_supported_type("custom_id", r"^\d{5}$", namespace="my-extension")
```

**Parameters:**
- `type` (str): The name of the type to register
- `regex` (str | None): A regex pattern for validating values of this type (optional)
- `namespace` (str | None): A namespace to group the type under (optional)

**Namespaced Types:**

Types registered with a namespace are stored as `namespace/type` (e.g., `my-extension/custom_id`). This helps avoid naming conflicts with core types or other extensions.

**Types Without Regex:**

Some types don't require pattern validation. Set `regex=None` for these cases:

```python
add_supported_type("generic_id", regex=None)
```

## Enabling Extensions

Extensions are enabled through Clue's main configuration file:

```yaml
# /etc/clue/conf/config.yml
core:
  extensions:
    - "my-extension"
    - "another-extension"
```

When Clue starts, it will:

1. Look for a module named `my-extension`
2. Load the `config` object from `my-extension.config`
3. Call the `init` function if defined
4. Register any routes specified in the configuration
5. Register the OBO module if defined

## Extension Loading Process

The extension loading sequence is as follows:

1. **Configuration Loading**: Clue reads `core.extensions` from the main config file
2. **Module Import**: For each extension, Clue imports `<extension-name>.config`
3. **Validation**: The extension's YAML configuration is loaded and validated
4. **Initialization**: If an `init` module is defined, it's called with the Flask app
5. **Route Registration**: Any routes defined in the extension are registered with Flask
6. **OBO Registration**: If an `obo_module` is defined, it's registered for token exchange

## Best Practices

### 1. Use Proper Logging

Always use Clue's logging infrastructure:

```python
from clue.common.logging import get_logger

logger = get_logger(__file__)

def my_function():
    logger.info("Processing started")
    logger.error("An error occurred: %s", error_message)
```

### 2. Handle Errors Gracefully

Extension failures shouldn't crash the entire application:

```python
def initialize(flask_app):
    try:
        # Your initialization logic
        setup_resources()
    except Exception as e:
        logger.exception("Failed to initialize extension: %s", e)
        # Don't re-raise - allow Clue to continue
```

### 3. Use Namespaces for Custom Types

Avoid naming conflicts by using namespaced types:

```python
# Good: Uses namespace
add_supported_type("user_id", r"^\d{8}$", namespace="my-extension")

# Risky: Could conflict with core or other extensions
add_supported_type("user_id", r"^\d{8}$")
```

### 4. Document Your Extension

Include clear documentation in your extension:

```python
"""
My Extension for Clue

This extension adds support for processing custom ticket IDs and provides
integration with the external ticketing system.

Configuration:
    - feature_x: Enable experimental feature X

Routes:
    - GET /api/v1/tickets/status/<ticket_id>
    - POST /api/v1/tickets/create

Custom Types:
    - ticket_id: Format TICKET-######
    - case_id: Format CASE-########
"""
```

### 5. Test Your Extension

Create comprehensive tests for your extension following the patterns in Clue's test suite:

```python
# test/test_my_extension.py
import pytest
from clue.extensions import EXTENSIONS

@pytest.fixture
def mock_extension():
    from my_extension.config import config
    EXTENSIONS["my-extension"] = config
    yield
    del EXTENSIONS["my-extension"]

def test_extension_initialization(mock_extension):
    """Test that the extension initializes correctly."""
    # Your test logic
    pass
```

## Example: Complete Extension

Here's a complete example extension that demonstrates all features:

### Directory Structure

```
ticket_extension/
├── __init__.py
├── config.py
├── init.py
├── obo.py
├── extension.yml
└── routes/
    └── ticket_route.py
```

### extension.yml

```yaml
name: "ticket-extension"

features:
  enable_notifications: true
  enable_auto_assign: false

modules:
  init: "ticket_extension.init:initialize"
  routes:
    - "ticket_route"
  obo_module: true
```

### config.py

```python
from pathlib import Path
from pydantic_settings import SettingsConfigDict
from clue.extensions.config import BaseExtensionConfig

class TicketExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "extension.yml",
        yaml_file_encoding="utf-8",
        strict=True
    )

config = TicketExtensionConfig(name="ticket-extension")
```

### init.py

```python
from clue.constants.supported_types import add_supported_type
from clue.common.logging import get_logger

logger = get_logger(__file__)

def initialize(flask_app):
    """Initialize the ticket extension."""
    logger.info("Initializing ticket-extension")

    # Register custom types
    add_supported_type("ticket_id", r"^TICKET-\d{6}$", namespace="ticket-extension")
    add_supported_type("case_id", r"^CASE-\d{8}$", namespace="ticket-extension")

    logger.info("Registered custom ticket types")
    logger.info("Ticket extension initialized successfully")
```

### routes/ticket_route.py

```python
from typing import Any
from clue.api import make_subapi_blueprint, ok, fail
from clue.common.logging import get_logger

SUB_API = "tickets"
ticket_route = make_subapi_blueprint(SUB_API, api_version=1)
ticket_route._doc = "Ticket Management API"

logger = get_logger(__file__)

@ticket_route.route("/status/<ticket_id>", methods=["GET"])
def get_ticket_status(ticket_id: str, **kwargs) -> tuple[dict[str, Any], int]:
    """
    Get the status of a ticket.

    Args:
        ticket_id: The ticket ID to query

    Returns:
        API response with ticket status
    """
    # Your logic to fetch ticket status
    return ok({
        "ticket_id": ticket_id,
        "status": "open",
        "assignee": "analyst1"
    })

@ticket_route.route("/create", methods=["POST"])
def create_ticket(**kwargs) -> tuple[dict[str, Any], int]:
    """
    Create a new ticket.

    Returns:
        API response with new ticket details
    """
    # Your logic to create a ticket
    return ok({
        "ticket_id": "TICKET-123456",
        "status": "created"
    })
```

### obo.py

```python
import requests
from clue.common.logging import get_logger

logger = get_logger(__file__)

def get_obo_token(service: str, access_token: str, user: str) -> str | None:
    """Get an OBO token for ticket system services."""
    if service != "ticket-system":
        return None

    try:
        response = requests.post(
            "https://tickets.example.com/auth/obo",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"user": user}
        )

        if response.status_code == 200:
            return response.json()["token"]
        else:
            logger.error("OBO exchange failed: %s", response.text)
            return None

    except Exception as e:
        logger.exception("Exception during OBO exchange: %s", e)
        return None
```

## Troubleshooting

### Extension Not Loading

Check the following:

1. Extension is listed in `core.extensions` in the main config
2. The extension module is on Python's sys.path
3. The `config.py` file exports a `config` object
4. Check logs for import errors

### Routes Not Accessible

Verify:

1. Routes are listed in the extension's `modules.routes`
2. Route module exports a Blueprint object
3. Check logs for "Enabling additional endpoint" messages
4. Ensure proper URL structure (`/api/v1/<subapi>/<endpoint>`)

### Custom Types Not Recognized

Ensure:

1. Types are registered in the `init` function
2. The `init` function is being called (check logs)
3. Regex patterns are valid Python regex
4. Namespace is correctly specified if used

## Security Considerations

### 1. Authentication

Routes should validate user authentication:

```python
from clue.security import requires_auth

@ticket_route.route("/sensitive", methods=["GET"])
@requires_auth()
def sensitive_endpoint(**kwargs):
    # Your protected endpoint logic
    pass
```

### 2. Input Validation

Always validate and sanitize inputs:

```python
import re

@ticket_route.route("/process/<ticket_id>", methods=["GET"])
def process_ticket(ticket_id: str, **kwargs):
    # Validate format
    if not re.match(r"^TICKET-\d{6}$", ticket_id):
        return fail("Invalid ticket ID format"), 400

    # Process the ticket
    pass
```

### 3. Error Handling

Don't expose sensitive information in error messages:

```python
try:
    result = external_api_call()
except Exception as e:
    logger.exception("External API call failed")
    return fail("Service temporarily unavailable"), 503
```

## Performance Tips

### 1. Lazy Loading

Load heavy resources only when needed:

```python
_heavy_resource = None

def get_heavy_resource():
    global _heavy_resource
    if _heavy_resource is None:
        _heavy_resource = load_heavy_resource()
    return _heavy_resource
```

### 2. Caching

Use Clue's caching infrastructure:

```python
from clue.cache import cache

@cache.memoize(timeout=300)
def expensive_operation(param):
    # Your expensive operation
    pass
```

### 3. Background Tasks

For long-running operations, consider using background tasks or queues rather than blocking API requests.

## API Reference

### BaseExtensionConfig

Base class for extension configuration.

**Attributes:**
- `name` (str): Extension name
- `features` (dict[str, bool]): Feature flags
- `modules` (Modules): Extension modules configuration

### Modules

Extension modules configuration.

**Attributes:**
- `init` (ImportString | None): Initialization function
- `routes` (list[ImportString]): List of route modules
- `obo_module` (ImportString | None): OBO authentication module

### add_supported_type

Register a custom data type.

```python
def add_supported_type(
    type: str,
    regex: str | None = None,
    namespace: str | None = None
) -> None
```

**Parameters:**
- `type`: Type name
- `regex`: Validation regex pattern (optional)
- `namespace`: Type namespace (optional)

## Additional Resources

- [Clue API Development Guide](development.en.md)
- [Plugin Development Guide](../../plugins/)
- [Test Examples](../../api/test/integration/extensions/)
