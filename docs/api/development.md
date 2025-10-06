# Clue API Development Guide

This guide outlines how to set up a development environment for the Clue API.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python 3.10, 3.11, or 3.12 (3.12 recommended)
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- Docker and Docker Compose for test dependencies
- Git

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/CybercentreCanada/clue.git
cd clue/api
```

### 2. Install Poetry

If you don't have Poetry installed, follow the [official installation guide](https://python-poetry.org/docs/#installation).

Verify Poetry installation:

```bash
poetry --version
```

### 3. Set Up Python Environment

Configure Poetry to use Python 3.12 (or your preferred version):

```bash
poetry env use 3.12
```

Verify the environment:

```bash
poetry env info
```

### 4. Install Dependencies

Install all dependencies including development and test dependencies:

```bash
poetry install --all-extras --with test,dev,types
```

This will install:

- Core dependencies
- Server extras (Werkzeug, bcrypt, PyYAML, etc.)
- Test dependencies (pytest, mypy, coverage, etc.)
- Development dependencies (pre-commit, ruff, etc.)
- Type checking dependencies

### 5. Create Required Directories and Configuration

Create the necessary directories for Clue configuration and logs:

```bash
sudo mkdir -p /etc/clue/conf/
sudo mkdir -p /etc/clue/lookups/
sudo mkdir -p /var/log/clue
sudo chmod a+rw /etc/clue/conf/
sudo chmod a+rw /etc/clue/lookups/
sudo chmod a+rw /var/log/clue
```

Copy configuration files:

```bash
cp build_scripts/classification.yml /etc/clue/conf/classification.yml
cp test/unit/config.yml /etc/clue/conf/config.yml
```

### 6. Start Test Dependencies

Start the required services (Redis and Keycloak) using Docker Compose:

```bash
cd dev
docker-compose up --build -d
cd ..
```

Wait for services to be healthy:

```bash
poetry run python build_scripts/keycloak_health.py
```

## Development Workflow

### Code Quality and Formatting

The project uses several tools to maintain code quality:

```bash
# Check formatting
poetry run ruff format clue --diff

# Apply formatting
poetry run ruff format clue

# Run linter checks
poetry run ruff check clue

# Fix auto-fixable issues
poetry run ruff check clue --fix

# Run type checking
poetry run type_check

# Run all tests
poetry run test
```

#### Test Specific Files or Functions

```bash
# Run specific test files
poetry run pytest test/unit/test_specific_module.py

# Run specific test functions
poetry run pytest test/unit/test_specific_module.py::test_function_name
```

### Starting the Development Server

Start the Clue API server:

```bash
poetry run server
```

The server will start and be available at the configured port, usually 5000 (check your config.yml anmd environment variables for details).

### Testing Enrichment Services

For testing connections to plugins from the central API, you may need to start additional test servers:

```bash
# Terminal 1
poetry run flask --app test.utils.test_server run --no-reload --port 5008

# Terminal 2
poetry run flask --app test.utils.bad_server run --no-reload --port 5009

# Terminal 3
poetry run flask --app test.utils.slow_server run --no-reload --port 5010

# Terminal 4
poetry run flask --app test.utils.telemetry_server run --no-reload --port 5011
```

## Project Structure

```text
api/
├── clue/              # Main application code
│   ├── api/           # API endpoints
│   ├── cache/         # Caching utilities
│   ├── common/        # Common utilities and helpers
│   ├── constants/     # Application constants
│   ├── cronjobs/      # Scheduled tasks
│   ├── extensions/    # Flask extensions
│   ├── helper/        # Helper modules
│   ├── models/        # Data models
│   ├── plugin/        # Plugin system
│   ├── remote/        # Remote service integrations
│   ├── security/      # Security modules
│   └── services/      # Business logic services
├── build_scripts/     # Build and utility scripts
├── dev/               # Development environment files
├── docs/              # Documentation
├── scripts/           # Utility scripts
└── test/              # Test files
    ├── integration/   # Integration tests
    ├── unit/          # Unit tests
    └── utils/         # Test utilities
```

## Available Poetry Scripts

The project defines several convenient scripts in `pyproject.toml`:

- `poetry run server` - Start the Clue API server
- `poetry run test` - Run the test suite
- `poetry run type_check` - Run type checking
- `poetry run coverage_report` - Generate coverage reports (must be run after `test`)
- `poetry run plugin` - Interactive plugin management

## Configuration

### Environment Variables

The following environment variables can override configuration settings:

- `CLUE_CONFIG_PATH` - Path to the main configuration file (default: `/etc/clue/conf/config.yml`)
- `CLUE_CLASSIFICATION_PATH` - Path to the classification file (default: `/etc/clue/conf/classification.yml`)
- `CLUE_PLUGIN_DIRECTORY` - Path to where clue extensions to the central API are stored (default: `/etc/clue/plugins`)
- `CLUE_SESSION_COOKIE_SAMESITE` - Set SameSite attribute for session cookies. Must be `Strict`, `Lax`, or `None` for security
- `CLUE_HSTS_MAX_AGE` - HTTP Strict Transport Security max-age value in seconds for enhanced HTTPS security
- `FLASK_ENV` - Flask environment (development/production)
- `FLASK_DEBUG` - Enable Flask debug mode
- `REDIS_HOST` - Override Redis hostname
- `REDIS_PORT` - Override Redis port

### Configuration Files

Clue uses two main configuration files:

- `/etc/clue/conf/config.yml` - Main application configuration
- `/etc/clue/conf/classification.yml` - Classification configuration

#### Main Configuration (`config.yml`)

The main configuration file defines all aspects of the Clue API server. Here are the key sections:

##### API Configuration

```yaml
api:
  # Security settings
  secret_key: "your-secret-key-here"  # Flask secret key for sessions
  session_duration: 3600              # Session duration in seconds (1 hour)
  validate_session_ip: true           # Validate session IP matches
  validate_session_useragent: true    # Validate session user agent matches
  validate_session_xsrf_token: true   # Enable XSRF token validation

  # Debugging and auditing
  debug: false                        # Enable Flask debug mode
  audit: true                         # Log API calls for auditing

  # Service discovery
  discover_url: null                  # Optional service discovery URL

  # External enrichment sources
  external_sources: []                # List of external enrichment services

  # OAuth on Behalf (OBO) targets
  obo_targets: {}                     # Services that Clue can OBO to
```

##### Authentication Configuration

```yaml
auth:
  # API Key authentication
  allow_apikeys: false               # Enable API key authentication
  apikeys:                          # Map of API keys to user identifiers
    "api-key-1": "user1"
    "api-key-2": "user2"

  # OAuth settings
  oauth:
    enabled: false                   # Enable OAuth authentication
    gravatar_enabled: false          # Enable Gravatar for user avatars
    other_audiences: []              # Additional JWT audiences to accept
    providers: {}                    # OAuth provider configurations

  # Service account authentication
  service_account:
    enabled: false                   # Enable service account authentication
    accounts: []                     # List of service account credentials

  # Token propagation
  propagate_clue_key: true          # Include Clue token in OBO requests
```

##### Core Services Configuration

```yaml
core:
  # Redis configuration
  redis:
    host: "127.0.0.1"               # Redis server hostname
    port: 6379                      # Redis server port

  # Extensions to load
  extensions: []                    # List of Clue extensions to load

  # Metrics collection
  metrics:
    export_interval: 5              # Metrics export interval in seconds
    redis:                          # Redis instance for metrics
      host: "127.0.0.1"
      port: 6379
    apm_server:                     # Application Performance Monitoring
      server_url: null              # APM server URL
      token: null                   # APM authentication token
```

##### Logging Configuration

```yaml
logging:
  # Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL, DISABLED
  log_level: "DEBUG"                # Current log level

  # Output destinations
  log_to_console: true              # Log to console/stdout
  log_to_file: false                # Log to files
  log_to_syslog: false              # Log to syslog server

  # File logging settings
  log_directory: "/var/log/clue/"   # Directory for log files
  log_as_json: false                # Use JSON format for logs

  # Syslog settings
  syslog_host: "localhost"          # Syslog server hostname
  syslog_port: 514                  # Syslog server port

  # Health monitoring
  heartbeat_file: null              # File to touch for health checks
  export_interval: 5                # Counter logging interval
```

##### UI Configuration

```yaml
ui:
  cors_origins: []                  # Allowed CORS origins for web UI
```

##### External Source Configuration

When configuring external enrichment sources, each source supports these options:

```yaml
api:
  external_sources:
    - name: "example-source"              # Unique source name
      url: "https://api.example.com"      # Source API URL
      classification: "TLP:CLEAR"         # Minimum classification level
      max_classification: "TLP:RED"       # Maximum classification level
      include_default: true               # Include in default queries
      production: false                   # Production-ready flag
      default_timeout: 30                 # Request timeout in seconds
      built_in: true                      # Built-in source flag
      maintainer: "Admin <admin@example.com>"  # RFC-5322 contact
      documentation_link: "https://docs.example.com"  # Documentation URL
      datahub_link: "https://datahub.example.com"      # DataHub entry
      obo_target: null                    # OBO target name
```

##### OAuth Provider Configuration

For OAuth authentication, configure providers like this:

```yaml
auth:
  oauth:
    enabled: true
    providers:
      keycloak:
        client_id: "clue-api"                    # OAuth client ID
        client_secret: "your-client-secret"     # OAuth client secret
        audience: "clue-api"                     # JWT audience
        scope: "openid profile email groups"    # OAuth scopes
        jwks_uri: "https://auth.example.com/realms/clue/protocol/openid-connect/certs"
        access_token_url: "https://auth.example.com/realms/clue/protocol/openid-connect/token"
        authorize_url: "https://auth.example.com/realms/clue/protocol/openid-connect/auth"
        api_base_url: "https://auth.example.com/realms/clue/protocol/openid-connect"

        # User management
        auto_create: true                        # Auto-create users
        auto_sync: false                         # Auto-sync user data
        required_groups: ["clue-users"]          # Required OAuth groups

        # Role and classification mapping
        role_map:                                # Map OAuth groups to Clue roles
          "clue-admins": "admin"
          "clue-analysts": "analyst"
        classification_map:                      # Map OAuth groups to clearance levels
          "clue-admins": "TLP:RED"
          "clue-analysts": "TLP:AMBER"

        # User ID configuration
        uid_randomize: false                     # Generate random usernames
        uid_regex: "^(.+)@example\\.com$"       # Extract username from email
        uid_format: "{0}"                        # Username format string
```

#### Classification Configuration (`classification.yml`)

The classification configuration defines the data classification system used by Clue. This file follows the Assemblyline classification engine format.

For detailed information on configuring the classification engine, see the [Assemblyline Classification Engine Documentation](https://cybercentrecanada.github.io/assemblyline4_docs/installation/classification_engine/).

Key aspects of classification configuration:

- **Classification Levels**: Define hierarchical classification levels (e.g., TLP:CLEAR, TLP:GREEN, TLP:AMBER, TLP:RED)
- **Required Classifications**: Specify minimum classification levels for different data types
- **Enforcement Rules**: Configure how classifications are enforced and propagated
- **Marking Schemes**: Define visual and textual markings for classified data

Example basic classification configuration:

```yaml
classification:
  enforce: true
  dynamic_groups: false
  levels:
    - TLP:CLEAR
    - TLP:GREEN
    - TLP:AMBER
    - TLP:RED
  required:
    - TLP:CLEAR
  groups:
    - name: "TLP"
      short_name: "TLP"
      description: "Traffic Light Protocol"
      auto_select: true
```

#### Configuration Validation

Clue validates configuration against a JSON schema on startup. If configuration is invalid, the server will fail to start with descriptive error messages indicating which settings need correction.

## Docker Development

### Building the Docker Image

Build the development Docker image:

```bash
poetry build
docker build -t clue-api:dev .
```

### Docker Compose for Full Stack

The development environment uses Docker Compose to provide essential services for testing and development. The `api/dev/docker-compose.yml` file defines the following services:

#### Redis Service

```yaml
redis:
  image: redis
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Purpose**: Redis serves as the caching layer and session store for Clue. It's used for:

- Session management and user authentication state
- Caching enrichment results to improve performance
- Rate limiting and quota management
- Metrics aggregation and temporary data storage

**Development Notes**:

- Exposed on the standard port 6379
- Includes health checks to ensure the service is ready before tests run
- No persistence configured - data is lost when container stops (suitable for development)

#### Keycloak Service (Custom Build)

```yaml
keycloak:
  build:
    context: ./keycloak
    dockerfile: Dockerfile
    no_cache: true
  environment:
    KC_HEALTH_ENABLED: true
  ports:
    - "9100:8080"
  expose:
    - "9100"
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8080/health/ready"]
    interval: 5s
    timeout: 5s
    retries: 15
```

**Purpose**: Keycloak provides OAuth/OpenID Connect authentication services for testing authentication flows in Clue.

**Custom Dockerfile Features**:
The custom Keycloak image (`api/dev/keycloak/Dockerfile`) extends the official Keycloak 18.0.2 image with:

- **Pre-configured Admin Account**:
  - Username: `admin`
  - Password: `admin`
  - Allows immediate access to Keycloak admin console

- **Development Mode**: Runs in development mode with debug enabled for easier troubleshooting

- **Pre-imported Realm**: Automatically imports the included realm configuration from `keycloak-realm.json`

- **Enhanced Features**: Enables token exchange and fine-grained authorization features that may be used by Clue

**Pre-configured Test Users**:
The imported realm includes several test users for development and testing:

- `admin` - Administrative user
- `dewey`, `donald`, `goose` - Standard test users
- `guest` - Guest user with limited permissions
- `huey`, `louie` - Additional test users

**Realm Configuration Highlights**:
The `keycloak-realm.json` file configures a built-in realm with:

- **Client Applications**: Pre-configured OAuth clients for Clue API integration
- **User Groups**: Different user groups with varying permission levels
- **Authentication Flows**: Standard OAuth flows for web and API authentication
- **Security Settings**: Appropriate security headers and session management
- **Internationalization**: Support for English and French locales
- **Token Lifespans**: Configured for development (shorter lifespans for testing)

#### Starting the Development Stack

To start all development services:

```bash
cd api/dev
docker-compose up --build -d
```

To verify services are healthy:

```bash
# Check service status
docker-compose ps

# Check logs if needed
docker-compose logs redis
docker-compose logs keycloak

# Or use the built-in health check
poetry run python build_scripts/keycloak_health.py
```

#### Accessing Services

- **Redis**: Available at `localhost:6379` (no authentication required)
- **Keycloak Admin Console**: `http://localhost:9100/admin`
  - Username: `admin`
  - Password: `admin`
- **Keycloak Realm**: `http://localhost:9100/realms/HogwartsMini`

#### Stopping and Cleaning Up

```bash
# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Rebuild from scratch
docker-compose down -v && docker-compose up --build
```

#### Integration with Clue API

When the Clue API is configured for OAuth authentication, it can connect to the local Keycloak instance using:

```yaml
auth:
  oauth:
    enabled: true
    providers:
      keycloak:
        client_id: "clue-api"
        jwks_uri: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/certs"
        access_token_url: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/token"
        authorize_url: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/auth"
        api_base_url: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect"
        # ... other configuration
```

This setup provides a complete development environment for testing authentication, authorization, caching, and all Clue API functionality without requiring external services.

## Contributing

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks before commits:

```bash
poetry run pre-commit install
```

### Branch Strategy

The Clue project follows a Git flow branching model to ensure stable releases and organized development:

#### Main Branches

- **`main`**: Contains production-ready code. All releases are tagged from this branch. Direct commits to `main` are restricted.
- **`develop`**: The integration branch for new features and the primary development branch. All feature branches are created from and merged back into `develop`.

#### Supporting Branches

- **Feature branches**: Created from `develop` for new features or enhancements. Use descriptive names like `feature/add-oauth-provider` or `feature/improve-caching`.
- **Release branches**: Created from `develop` when preparing for a new release (e.g., `release/v2.1.0`). Used for final testing and minor bug fixes.
- **Hotfix branches**: Created from `main` for critical bug fixes that need immediate deployment (e.g., `hotfix/security-patch`).

#### Development Workflow

1. **Feature Development**: Create a feature branch from `develop`
2. **Integration**: Merge completed features into `develop` via pull request
3. **Release Preparation**: Create a release branch from `develop` when ready for release
4. **Production Release**: Merge release branch into both `main` and `develop`, then tag the release
5. **Hotfixes**: If critical issues are found in production, create hotfix branches from `main`

### Pull Request Process

All code changes must go through the pull request process to ensure code quality and maintain project standards:

#### For Contributors with Write Access

1. **Create Feature Branch**: Create a new branch from `develop` with a descriptive name

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Implement Changes**: Make your changes, following the project's coding standards and including appropriate tests

3. **Pre-submission Checks**: Before opening a PR, ensure:
   - All tests pass: `poetry run test`
   - Code is properly formatted: `poetry run ruff format clue`
   - Linting passes: `poetry run ruff check clue`
   - Type checking passes: `poetry run type_check`

   Note that installing pre-commit hooks will also help handle these cases.

4. **Open Pull Request**: Create a PR targeting the `develop` branch with:
   - Clear, descriptive title
   - Detailed description of changes
   - Reference to any related issues
   - Screenshots or examples if applicable

#### For External Contributors

1. **Fork Repository**: Fork the Clue repository to your GitHub account

2. **Clone and Setup**: Clone your fork and set up the development environment as described in this guide

3. **Create Feature Branch**: Create a branch from `develop` in your fork

4. **Implement and Test**: Make your changes and ensure all checks pass

5. **Submit Pull Request**: Open a PR from your fork's feature branch to the main repository's `develop` branch

#### Review Process

- **Required Approvals**: All pull requests require **at least two approvals** from project maintainers
- **Automated Checks**: PRs must pass all automated checks including:
  - Unit tests and integration tests
  - Code formatting and linting
  - Type checking
  - Security scans

- **Code Review**: Reviewers will examine:
  - Code quality and adherence to project standards
  - Test coverage and quality
  - Documentation updates if needed
  - Security implications
  - Performance considerations

#### Merge and Release

- **Merge to Develop**: Once approved and all checks pass, the PR is merged into `develop`
- **Release Cycle**: Features merged into `develop` will be included in the next release when `develop` is merged into `main`
- **Release Timeline**: Release schedules are determined by the project maintainers based on feature readiness and testing completion. There's no guaranteed duration from merge to release.

#### Best Practices

In order to maintain high code quality in clue:

- Keep PRs focused and reasonably sized
- Include comprehensive test coverage for new features
- Update documentation for user-facing changes
- Rebase your branch if requested to maintain a clean history
  - All PRs will be squash merged into the trunk.

## Troubleshooting

### Environment Issues

If you encounter issues with the Python environment:

1. Delete the existing environment: `poetry env remove python`
2. Recreate it: `poetry env use 3.12`
3. Reinstall dependencies: `poetry install --all-extras --with test,dev,types`

### Service Dependencies

If Docker services aren't starting properly:

1. Stop all containers: `docker-compose down`
2. Remove volumes: `docker-compose down -v`
3. Rebuild: `docker-compose up --build`

## Additional Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Getting Help

You can reach the Clue developemnt team on the CCCS aurora discord: <https://discord.gg/GUAy9wErNu>
