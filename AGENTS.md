# Clue Agent Guide

## Repository Shape

- This is a multi-package repository; each Python package has its own Poetry environment and lockfile.
- `api/` is the central Clue API (Flask, Python 3.12). Entry point is `api/clue/app.py` (`poetry run server`). It also
  ships the `clue.plugin` framework (`CluePlugin` in `api/clue/plugin/__init__.py`) that every plugin builds on.
- `plugins/` holds independent enrichment services. Each plugin is a small Flask app with its own `requirements.txt`
  (where needed); plugins run against the API's Poetry environment. `plugins/setup/` holds the plugin scaffolding and
  interactive test tooling.
- `ui/` is the Clue UI, a React/Vite TypeScript app that is also published to npm as `@cccsaurora/clue-ui`
  (`pnpm build-lib`). Code under `ui/src/lib/` is the exported library surface.
- `ui/src/commons/` is vendored shared UI code; avoid reformatting or refactoring it beyond what a task needs.
- `mcp/` is the Clue MCP server (`clue_mcp`).
- `mkdocs/` is the MkDocs documentation site (English and French, `*.fr.md`). Release notes live in
  `mkdocs/docs/releases/`.
- `helm/` and `demo/` hold deployment charts and a local demo stack.

## Toolchains And Setup

- `make setup` installs pnpm, Poetry, and both UI and API dependencies. `make help` lists the other targets.
- Use Poetry for every Python package; do not install Python dependencies from the repository root.
- Python quality jobs run on Python 3.12. API tests run on 3.10-3.13.
- The UI uses Node 24 (`ui/.nvmrc`) and pnpm 11 in CI. Use pnpm, never npm, and honor `ui/pnpm-lock.yaml`.
- After changing a lockfile or dependency declaration, reinstall that package from its lockfile before validating it.
- Install the git hooks with `poetry run pre-commit install` from `api/`. This installs both the `pre-commit` and
  `commit-msg` hooks defined in `.pre-commit-config.yaml`; hook scripts live in `hooks/`.

## Commits And Pull Requests

- Use Conventional Commits (`feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore`, ...). The
  `commit-msg` hook validates this and lowercases the summary; PR titles are checked by `pr-title-check.yml`.
- Scopes are optional and free-form; common ones are `api`, `ui`, `mcp`, `plugin`, `ci`, or a plugin name.

## API Development And Validation

Run these from `api/` after `poetry install --all-extras --with test,dev,types`:

```bash
poetry run ruff format clue --diff
poetry run ruff check clue --output-format=github
poetry run type_check
poetry run test <pytest args>
```

- `make start-dependencies` starts Redis, MongoDB, and Keycloak from `api/dev/docker-compose.yml`.
- API tests expect writable `/etc/clue/conf/` and `/var/log/clue/`. Copy `build_scripts/classification.yml` and
  `test/unit/config.yml` into `/etc/clue/conf/` before testing (see `.github/workflows/api-workflow.yml`).
- `poetry run test` starts several local test plugin servers (ports 5008-5012) before running pytest with coverage;
  extra arguments are forwarded to pytest. Prefer targeted tests over the full suite during routine validation.
- Endpoints are Flask Blueprints under `api/clue/api/v1/` registered in `api/clue/app.py`. Return responses through
  the `clue.api` helpers (`ok`, `created`, `bad_request`, ...) and protect routes with `@clue.security.api_login(...)`.
- Configuration is Pydantic settings loaded from `/etc/clue/conf/config.yml` (`api/clue/models/config.py`).

## Plugin Development And Validation

- `make create-plugin` scaffolds a new plugin; `make test-plugin <plugin_dir>` runs one interactively.
- Plugin tests run from `api/` using the API environment:
  `poetry run python -m pytest ../plugins/<name> -c ../plugins/pytest.ini`.
- Plugins are linted with `ruff format`, `ruff check`, and `mypy` (see `.github/workflows/lint-plugin.yml`).

## UI Development And Validation

Run these from `ui/`:

```bash
pnpm install --frozen-lockfile
python ../hooks/check_translation.py
python ../hooks/find_bad_imports.py
pnpm tsc --noEmit
pnpm oxfmt src --check
pnpm oxlint src
pnpm test <specific_test_file_paths>
```

- Formatting is oxfmt (`ui/.oxfmtrc.json`) and linting is type-aware oxlint (`ui/.oxlintrc.json`). `pnpm lint` fixes
  both. Do not reintroduce Prettier or ESLint.
- Keep English and French translations (`ui/src/locales/{en,fr}/translation.json`) in sync.
- `hooks/find_bad_imports.py` bans imports that break downstream consumers of the library in `ui/src/lib/` (for
  example `@mui/icons-material` and unguarded `process.env`).
- Prefer targeted tests over the full UI suite during routine validation.

## MCP Development And Validation

Run these from `mcp/` after `poetry install --with dev`:

```bash
poetry run ruff format clue_mcp --diff
poetry run ruff check .
poetry run test
```

- Network tests need the full stack from `mcp/docker-compose.yml` (`--profile full`).
