# Copilot instructions (Clue)

Read and follow [`AGENTS.md`](../AGENTS.md) at the repository root. It describes the repository layout, toolchains,
and the validation commands CI runs for each package.

## Extensions, plugins, and external sources
- **Extensions (in-process)**: `config.core.extensions` lists Python modules. Each module must export `config` from `<extension>.config` (a `BaseExtensionConfig`). At startup, Clue calls `modules.init` and registers any `modules.routes` Blueprints (see `api/clue/extensions/__init__.py`, `api/clue/extensions/config.py`, and `api/clue/app.py`).
- **External enrichment sources (out-of-process)**: configured via `config.api.external_sources` (`ExternalSource`: `url`, `classification`, `obo_target`, etc.; see `api/clue/models/config.py`).
- **OBO + quotas**: per-user concurrency quotas for OBO targets are enforced via Redis (`UserQuotaTracker`) in `api/clue/services/user_service.py`.
- **Errors**: Centralized error handlers live in `api/clue/error.py` (notably 401 clears `XSRF-TOKEN`).
- **Caching toggles**: `DISABLE_CACHE=true` disables some Redis/local caching paths (`api/clue/constants/env.py`).
