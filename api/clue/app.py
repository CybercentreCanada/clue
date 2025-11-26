from gevent import monkey

monkey.patch_all()

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# We append the plugin directory for howler to the python part
PLUGIN_PATH = Path(os.environ.get("CLUE_PLUGIN_DIRECTORY", "/etc/clue/plugins"))
sys.path.insert(0, str(PLUGIN_PATH))

from clue.config import DEBUG, SECRET_KEY, cache, config

if config.api.debug and PLUGIN_PATH.exists():
    for _plugin in PLUGIN_PATH.iterdir():
        sys.path.append(
            str(Path(os.path.realpath(_plugin)) / f"../.venv/lib/python3.{sys.version_info.minor}/site-packages")
        )

import logging
import os
import re
from typing import Any, cast

import elasticapm
from authlib.integrations.flask_client import OAuth
from elasticapm.contrib.flask import ElasticAPM
from flasgger import Swagger
from flask import Flask
from flask.blueprints import Blueprint
from flask.logging import default_handler
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from clue.api.base import api
from clue.api.v1 import apiv1
from clue.api.v1.actions import actions_api
from clue.api.v1.auth import auth_api
from clue.api.v1.configs import configs_api
from clue.api.v1.fetchers import fetchers_api
from clue.api.v1.lookup import lookup_api
from clue.api.v1.registration import registration_api
from clue.api.v1.static import static_api
from clue.common.logging import get_logger
from clue.cronjobs import setup_jobs as setup_cron_jobs
from clue.error import errors
from clue.extensions import get_extensions
from clue.healthz import healthz

SESSION_COOKIE_SAMESITE = os.environ.get("CLUE_SESSION_COOKIE_SAMESITE", None)
HSTS_MAX_AGE = os.environ.get("CLUE_HSTS_MAX_AGE", None)

logger = get_logger(__file__)

##########################
# App settings
current_directory = os.path.dirname(__file__)

app = Flask("clue_api")
# Disable strict check on trailing slashes for endpoints
app.url_map.strict_slashes = False
app.config["JSON_SORT_KEYS"] = False

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": make_wsgi_app()})  # type: ignore[method-assign]

swagger_template = {
    "info": {
        "title": "Clue API",
        "description": "Clue is designed to provide analysts with pertinent insights wherever they engage with "
        "data. It serves as a single portal for all enrichments, offering pro-active enrichment capabilities and "
        "on-demand execution and scaling. Clue also features advanced insight visualizations and reusable UI "
        "components to enhance the user experience and streamline analytic workflows.",
    }
}
swagger = Swagger(
    app,
    template=swagger_template,
    config={
        "headers": [],
        "static_url_path": "/api/swagger_static",
        "specs": [
            {
                "endpoint": "apispec_v1",
                "route": "/api/apispec_v1.json",
                "rule_filter": lambda rule: True,  # all in
                "model_filter": lambda tag: True,  # all in
            }
        ],
        "specs_route": "/api/docs",
    },
)

cache.init_app(app)

app.logger.setLevel(60)  # This completely turns off the flask logger

ssl_context = None
logger.debug("Using flask secret key %s", re.sub(r"(.{6}).+(.{6})", r"\1...\2", SECRET_KEY))
app.config.update(SESSION_COOKIE_SECURE=True, SECRET_KEY=SECRET_KEY, PREFERRED_URL_SCHEME="https")
if SESSION_COOKIE_SAMESITE:
    if SESSION_COOKIE_SAMESITE in ["Strict", "Lax"]:
        app.config.update(SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE)
    else:
        raise ValueError("SESSION_COOKIE_SAMESITE must be set to 'Strict', 'Lax', or None")

app.register_blueprint(healthz)
app.register_blueprint(api)
app.register_blueprint(apiv1)
app.register_blueprint(errors)
app.register_blueprint(auth_api)
app.register_blueprint(actions_api)
app.register_blueprint(configs_api)
app.register_blueprint(fetchers_api)
app.register_blueprint(lookup_api)
app.register_blueprint(registration_api)
app.register_blueprint(static_api)


logger.info("Checking plugins for additional routes")
for plugin in get_extensions():
    if not plugin.modules.routes:
        continue

    for route in cast(list[Blueprint], plugin.modules.routes):
        logger.info("Enabling additional endpoint: %s", route.url_prefix)
        app.register_blueprint(route)

# Setup OAuth providers
if config.auth.oauth.enabled:
    providers = []
    for name, provider in config.auth.oauth.providers.items():
        raw_provider: dict[str, Any] = provider.model_dump(mode="json", exclude_none=True)

        # Set provider name
        raw_provider["name"] = name

        # Remove clue specific fields from oAuth config
        raw_provider.pop("auto_create", None)
        raw_provider.pop("auto_sync", None)
        raw_provider.pop("user_get", None)
        raw_provider.pop("auto_properties", None)
        raw_provider.pop("uid_regex", None)
        raw_provider.pop("uid_format", None)
        raw_provider.pop("user_groups", None)
        raw_provider.pop("user_groups_data_field", None)
        raw_provider.pop("user_groups_name_field", None)
        raw_provider.pop("app_provider", None)

        # Add the provider to the list of providers
        providers.append(raw_provider)

    if providers:
        oauth = OAuth()
        for raw_provider in providers:
            oauth.register(**raw_provider)
        oauth.init_app(app)

if config.auth.allow_apikeys:
    logger.debug(f"Allowing API Key use. Registered keys: {','.join(config.auth.apikeys.keys())}")

# Setup logging
app.logger.setLevel(logger.getEffectiveLevel())
app.logger.removeHandler(default_handler)
if logger.parent:
    for ph in logger.parent.handlers:
        app.logger.addHandler(ph)

# Setup APMs
if config.core.metrics.apm_server.server_url is not None:
    app.logger.info(f"Exporting application metrics to: {config.core.metrics.apm_server.server_url}")
    ElasticAPM(
        app, client=elasticapm.Client(server_url=config.core.metrics.apm_server.server_url, service_name="enrichment")
    )

wlog = logging.getLogger("werkzeug")
wlog.setLevel(logging.WARNING)
if logger.parent:  # pragma: no cover
    for h in logger.parent.handlers:
        wlog.addHandler(h)

# setup Cronjob
setup_cron_jobs()


def main():
    """Runs the flask server"""
    app.jinja_env.cache = {}
    app.run(
        host="0.0.0.0",  # noqa: S104
        debug=DEBUG,
        port=int(os.getenv("FLASK_RUN_PORT", os.getenv("PORT", 5000))),
        ssl_context=ssl_context,
    )


if __name__ == "__main__":
    main()
