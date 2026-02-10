# Copilot instructions (Clue)

## Repo layout (monorepo)
- `api/`: central Clue API (Python 3.12, Flask). Entry point is `api/clue/app.py` (Poetry script: `server`).
- `plugins/`: independent enrichment services. Each plugin is a small Flask app built around `CluePlugin` (`api/clue/plugin/__init__.py`).
- `ui/`: Clue UI library (Node 20 + pnpm); CI runs prettier/eslint + unit tests (see `.github/workflows/ui-workflow.yml`).
- `mkdocs/`: documentation site (MkDocs Material + i18n).
- `helm/`, `demo/`: deployment and a local demo stack.

## API architecture & conventions (`api/`)
- **Configuration**: Pydantic settings loaded from `/etc/clue/conf/config.yml` (or `CLUE_CONF_FOLDER`), and classification from `classification.yml` (see `api/clue/models/config.py` and `api/clue/common/forge.py`).
- **Routing**: API endpoints are Flask Blueprints under `api/clue/api/v1/…` and are registered in `api/clue/app.py`.
- **Responses**: Return via `clue.api` helpers (`ok`, `created`, `bad_request`, …). These wrap data into the `ClueResponse` envelope and handle Pydantic `BaseModel` serialization (see `api/clue/api/__init__.py`).
- **Auth & protection**: Protect routes with `@clue.security.api_login(...)`. This decorator sets `protected`/`audit` flags used by `/api/site_map/` and other tooling (see `api/clue/api/base.py`).
- **Errors**: Centralized error handlers live in `api/clue/error.py` (notably 401 clears `XSRF-TOKEN`).
- **Caching toggles**: `DISABLE_CACHE=true` disables some Redis/local caching paths (`api/clue/constants/env.py`).

## Extensions, plugins, and external sources
- **Extensions (in-process)**: `config.core.extensions` lists Python modules. Each module must export `config` from `<extension>.config` (a `BaseExtensionConfig`). At startup, Clue calls `modules.init` and registers any `modules.routes` Blueprints (see `api/clue/extensions/__init__.py`, `api/clue/extensions/config.py`, and `api/clue/app.py`).
- **External enrichment sources (out-of-process)**: configured via `config.api.external_sources` (`ExternalSource`: `url`, `classification`, `obo_target`, etc.; see `api/clue/models/config.py`).
- **OBO + quotas**: per-user concurrency quotas for OBO targets are enforced via Redis (`UserQuotaTracker`) in `api/clue/services/user_service.py`.

## Developer workflows (what CI does)
- **One-time setup**: `make setup` (installs pnpm + Poetry and installs both UI + API deps).
- **Start dependencies**: `make start-dependencies` (Redis/MongoDB/Keycloak via `api/dev/docker-compose.yml`).
- **Run API**: `cd api && poetry run server`.
  - Local dev typically needs writable `/var/log/clue/` and config files under `/etc/clue/conf/` (see `api/README.md` and `.github/workflows/api-workflow.yml`).
- **Lint/format/typecheck**: `cd api && poetry run ruff format clue`, `poetry run ruff check clue`, `poetry run type_check`.
- **Tests**: `cd api && poetry run test`.
  - This spins up several local test plugin servers (ports 5008-5012) and then runs pytest/coverage (see `api/build_scripts/run_tests.py`).

## Plugin development helpers (`plugins/`)
- **Generate a plugin**: `make create-plugin` (wizard writes `manifest.yml`, `README.md`, optional `app.py`; see `plugins/setup/create.py`).
- **Interactive plugin testing**: `make test-plugin <plugin_dir>`.
  - Set `CLUE_ACCESS_TOKEN` to inject `Authorization: Bearer …` into test requests when your plugin calls external services (see `plugins/setup/interactive.py`).
