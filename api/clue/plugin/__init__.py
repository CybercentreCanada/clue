import inspect
import ipaddress
import json
import logging
import os
import time
from typing import Any, Callable, Literal, Self, Union, cast
from urllib import parse as ul

import gevent
import gevent.pool
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, make_response, request
from flask.globals import _cv_request
from gevent import Greenlet
from pydantic import BaseModel, TypeAdapter, ValidationError

from clue.cache import Cache
from clue.common.exceptions import (
    AuthenticationException,
    ClueException,
    ClueValueError,
    InvalidDataException,
    NotFoundException,
    TimeoutException,
    UnprocessableException,
)
from clue.common.logging.format import CLUE_DATE_FORMAT, CLUE_LOG_FORMAT
from clue.models.actions import (
    Action,
    ActionBase,
    ActionResult,
    ActionSpec,
    ExecuteRequest,
)
from clue.models.fetchers import FetcherDefinition, FetcherResult
from clue.models.network import QueryEntry
from clue.models.selector import Selector
from clue.plugin.helpers.token import get_username
from clue.plugin.models import BulkEntry
from clue.plugin.utils import Params

# Load environment variables from .env file if present
load_dotenv()

# List of function names that can be overridden using the @plugin.use decorator
# These functions define the core plugin behavior and can be customized per plugin
OVERRIDABLE_FUNCTIONS = [
    "enrich",  # Main enrichment function for processing selectors
    "alternate_bulk_lookup",  # Alternative bulk enrichment implementation
    "liveness",  # Kubernetes liveness probe endpoint
    "readyness",  # Kubernetes readiness probe endpoint
    "run_action",  # Function to execute plugin actions
    "run_fetcher",  # Function to execute plugin fetchers
    "setup_actions",  # Runtime action definition generation
    "validate_token",  # Custom authentication token validation
]


def default_validate_token():
    """A default validation function that extracts Bearer tokens from the Authorization header.

    This function is provided as a reference implementation but is not used by default.
    Plugin developers can use this as a starting point for their own token validation.

    Returns:
        tuple[str | None, str | None]: A tuple containing (token, error_message).
            - If successful: (extracted_token, None)
            - If failed: (None, error_description)

    Note:
        Expects Authorization header format: "Bearer <token>"
    """
    token = request.headers.get("Authorization", None, type=str)
    if token and " " in token:
        # Split "Bearer <token>" and extract the token part
        token = token.split()[1]

        if token:
            return token, None

    return None, "No bearer token was provided. Please provide a Bearer token in the Authorization header"


def liveness(**_):
    """Default liveness probe for Kubernetes health checks.

    This endpoint indicates whether the application is running and alive.
    Returns a simple "OK" response with 200 status code.

    Returns:
        Response: Flask response with "OK" message
    """
    return make_response("OK")


def readyness(**_):
    """Default readiness probe for Kubernetes health checks.

    This endpoint indicates whether the application is ready to serve traffic.
    Returns a simple "OK" response with 200 status code.

    Returns:
        Response: Flask response with "OK" message
    """
    return make_response("OK")


def build_default_logger() -> logging.Logger:
    """Configure a default logger with standard Clue formatting when none is provided.

    Creates a logger with INFO level that outputs to console using the standard
    Clue log format and date format for consistency across all plugins.

    Returns:
        logging.Logger: Configured logger instance ready for use

    Note:
        Uses logger name "clue.plugin.default" to distinguish from user-provided loggers
    """
    logger = logging.getLogger("clue.plugin.default")
    logger.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # Apply standard Clue log formatting for consistency
    console.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
    logger.addHandler(console)

    return logger


class CluePlugin:
    """Helper class for creating clue plugins with proper server responses and behaviour.

    Includes a default bulk lookup function that multithreads requests to the resource being queried.

    Attributes:
        alternate_bulk_lookup:
            Provides an alternative implementation for bulk enrichment.

            By default, clue plugins will split bulk enrichments into many parallel threads, allowing the plugin to
            use the same enrich function implemented without the need for complex bulk enrichment responses. However,
            in cases where it is necessary to streamline enrichment of bulk selectors (i.e. making hundreds of SQL
            queries instead of one), this alternate lookup function can be used.
        app:
            The underlying Flask object representing the server recieving and responding to requests from the
            central API.
        app_name:
            The name of this clue plugin. Used to configure the cache and for logging.
        cache:
            The instantiated cache for this clue plugin. Can be used directly to cache and retrieve additional data.
        classification:
            The classification level of selectors this plugin accepts.

            Enrichment requests exceeding this classification level will not be processed by this plugin.
        logger:
            The logging instance used internally.
        supported_types:
            The list of types supported by this plugin for enrichment.
        actions:
            A list of action definitions this plugin supports.
        setup_actions:
            An optional function called when a list of supported actions is asked for.

            Useful for runtime generation of actions - for example, returning a list of valid arguments that changes on
            a per-user basis. Can be used instead of the actions attribute.
        validate_token:
            A user-provided function for validating the authentication token provided from the central API.

            Can be used to ensure the audience matches the expected value, ensuring specific fields are present in the
            JWT, etc.
        enrich:
            The main enrichment function.

            Accepts the type and value of the selector, a list of parameters relevant to the enrichment, and the token
            provided from the central API (assuming authentication is enabled). Returns QueryEntry object(s) denoting
            the enrichments for the given selector.
        run_action:
            The main function for running actions.

            Accepts the selected action definition as well as the ExecuteRequest. If the Action definition's parameters
            were extended with a custom ExecuteRequest (i.e. to add additional user parameters) that instance will be
            passed instead, and casting the argument will be necessary.
        fetchers:
            A list of fetcher definitions this plugin supports.

        run_fetcher:
            The main function for running fetchers.

            Accepts the selected fetcher definition as well as the selector to execute the fetcher on. Returns a
            completed FetcherResult.
        liveness:
            A liveness probe for kubernetes implementations of clue.
        readyness:
            A readyness probe for kubernetes implementations of clue.
    """

    alternate_bulk_lookup: Callable[[list[dict[str, str]], Params], dict[str, dict[str, BulkEntry]]] | None
    """Provides an alternative implementation for bulk enrichment.

    By default, clue plugins will split bulk enrichments into many parallel threads, allowing the plugin to
    use the same enrich function implemented without the need for complex bulk enrichment responses. However,
    in cases where it is necessary to streamline enrichment of bulk selectors (i.e. making hundreds of SQL
    queries instead of one), this alternate lookup function can be used.
    """

    app: Flask
    "The underlying Flask object representing the server recieving and responding to requests from the central API."

    app_name: str
    "The name of this clue plugin. Used to configure the cache and for logging."

    cache: Cache | None
    "The instantiated cache for this clue plugin. Can be used directly to cache and retrieve additional data."

    classification: str
    """The classification level of selectors this plugin accepts.

    Enrichment requests exceeding this classification level will not be processed by this plugin.
    """

    logger: logging.Logger
    "The logging instance used internally."

    supported_types: set[str] | None
    "The list of types supported by this plugin for enrichment."

    actions: list[Action]
    "A list of action definitions this plugin supports."

    setup_actions: Callable[[list[Action], str | None], list[Action]] | None
    """An optional function called when a list of supported actions is asked for.

    Useful for runtime generation of actions - for example, returning a list of valid arguments that changes on a
    per-user basis. Can be used instead of the actions attribute.
    """

    validate_token: Callable[[], tuple[str | None, str | None]] | None
    """A user-provided function for validating the authentication token provided from the central API.

    Can be used to ensure the audience matches the expected value, ensuring specific fields are present in the
    JWT, etc.
    """

    enrich: Callable[[str, str, Params, str | None], Union[list[QueryEntry], QueryEntry]] | None
    """The main enrichment function.

    Accepts the type and value of the selector, a list of parameters relevant to the enrichment, and the token provided
    from the central API (assuming authentication is enabled). Returns QueryEntry object(s) denoting the enrichments for
    the given selector.
    """

    run_action: Callable[[Action, ExecuteRequest, str | None], ActionResult] | None
    """The main function for running actions.

    Accepts the selected action definition as well as the ExecuteRequest. If the Action definition's parameters were
    extended with a custom ExecuteRequest (i.e. to add additional user parameters) that instance will be passed instead,
    and casting the argument will be necessary.
    """

    fetchers: list[FetcherDefinition] | None
    "A list of fetcher definitions this plugin supports."

    run_fetcher: Callable[[FetcherDefinition, Selector, str | None], FetcherResult] | None
    """The main function for running fetchers.

    Accepts the selected fetcher definition as well as the selector to execute the fetcher on. Returns a completed
    FetcherResult.
    """

    liveness: Callable[[], Response]
    "A liveness probe for kubernetes implementations of clue."

    readyness: Callable[[], Response]
    "A readyness probe for kubernetes implementations of clue."

    def __init__(
        self: Self,
        app_name: str,
        actions: list[Action] = [],
        alternate_bulk_lookup: Callable[[list[dict[str, str]], Params], dict[str, dict[str, BulkEntry]]] | None = None,
        cache_timeout: int = 5 * 60,  # five minute timeout
        classification: str | None = os.environ.get("CLASSIFICATION", None),
        enable_apm: bool = False,
        enable_cache: Union[bool, Literal["redis"], Literal["local"]] = True,
        enrich: Callable[[str, str, Params, str | None], Union[list[QueryEntry], QueryEntry]] | None = None,
        fetchers: list[FetcherDefinition] | None = None,
        liveness: Callable[[], Response] = liveness,
        local_cache_options: dict[str, Any] | None = None,
        logger: logging.Logger | None = None,
        readyness: Callable[[], Response] = readyness,
        run_action: Callable[[Action, ExecuteRequest, str | None], ActionResult] | None = None,
        run_fetcher: Callable[[FetcherDefinition, Selector, str | None], FetcherResult] | None = None,
        setup_actions: Callable[[list[Action], str | None], list[Action]] | None = None,
        supported_types: set[str] | str | None = None,
        validate_token: Callable[[], tuple[str | None, str | None]] | None = None,
    ) -> None:
        """Helper class for creating clue plugins with proper server responses and behaviour.

        Includes a default bulk lookup function that multithreads requests to the resource being queried.

        Args:
            app_name:
                The name of this clue plugin. Used to configure the cache and for logging.
            actions:
                A list of action definitions this plugin supports.
            alternate_bulk_lookup:
                Provides an alternative implementation for bulk enrichment.

                By default, clue plugins will split bulk enrichments into many parallel threads, allowing the plugin
                to use the same enrich function implemented without the need for complex bulk enrichment responses.
                However, in cases where it is necessary to streamline enrichment of bulk selectors (i.e. making
                hundreds of SQL queries instead of one), this alternate lookup function can be used.
            cache_timeout:
                How long should the cache store cached data before purging it?
            classification:
                The classification level of selectors this plugin accepts.

                Enrichment requests exceeding this classification level will not be processed by this plugin.
            logger:
                The logging instance used internally.
            supported_types:
                The list of types supported by this plugin for enrichment.
            setup_actions:
                An optional function called when a list of supported actions is asked for.

                Useful for runtime generation of actions - for example, returning a list of valid arguments that
                changes on a per-user basis. Can be used instead of the actions attribute.
            validate_token:
                A user-provided function for validating the authentication token provided from the central API.

                Can be used to ensure the audience matches the expected value, ensuring specific fields are present in
                the JWT, etc.
            enrich:
                The main enrichment function.

                Accepts the type and value of the selector, a list of parameters relevant to the enrichment, and the
                token provided from the central API (assuming authentication is enabled). Returns QueryEntry object(s)
                denoting the enrichments for the given selector.
            run_action:
                The main function for running actions.

                Accepts the selected action definition as well as the ExecuteRequest. If the Action definition's
                parameters were extended with a custom ExecuteRequest (i.e. to add additional user parameters) that
                instance will be passed instead, and casting the argument will be necessary.
            fetchers:
                A list of fetcher definitions this plugin supports.

            run_fetcher:
                The main function for running fetchers.

                Accepts the selected fetcher definition as well as the selector to execute the fetcher on. Returns a
                completed FetcherResult.
            liveness:
                A liveness probe for kubernetes implementations of Clue.
            readyness:
                A readyness probe for kubernetes implementations of Clue.
        """
        self.alternate_bulk_lookup = alternate_bulk_lookup
        # Create Flask app using the module name (before first dot) as app name
        self.app = Flask(__name__.split(".")[0])
        self.app_name = app_name

        # Classification is required for security - must be specified via env var or parameter
        if classification is None:
            raise ClueValueError(
                "Classification must be specified, either via the CLASSIFICATION environment variable, or when "
                "intializing the plugin."
            )

        self.classification = classification
        self.liveness = liveness
        self.readyness = readyness

        # Convert comma-separated string to set for easier membership testing
        if isinstance(supported_types, str):
            self.supported_types = set(supported_types.split(","))
        else:
            self.supported_types = supported_types

        self.actions = actions
        self.setup_actions = setup_actions

        # Allow URLs with or without trailing slashes to match the same route
        self.app.url_map.strict_slashes = False

        self.logger = logger if logger else build_default_logger()

        self.enrich = enrich
        self.run_action = run_action
        self.validate_token = validate_token

        self.fetchers = fetchers
        self.run_fetcher = run_fetcher

        self.__init_routes()

        # Initialize Application Performance Monitoring if enabled
        if enable_apm:
            self.__init_apm()

        # Set up caching based on configuration
        if enable_cache:
            # Support both boolean (use default cache type) and explicit cache type specification
            if isinstance(enable_cache, bool):
                # Use environment variable or default to redis
                cache_type = cast(Union[Literal["redis"], Literal["local"]], os.environ.get("CACHE_TYPE", "redis"))
                self.cache = Cache(
                    self.app_name,
                    self.app,
                    cache_type,
                    timeout=cache_timeout,
                    local_cache_options=local_cache_options,
                )
            else:
                # Use explicitly specified cache type
                self.cache = Cache(
                    self.app_name,
                    self.app,
                    enable_cache,
                    timeout=cache_timeout,
                    local_cache_options=local_cache_options,
                )
        else:
            self.cache = None

        # Configure werkzeug (Flask's WSGI server) logging to reduce noise
        # Set to WARNING level to suppress INFO messages about HTTP requests
        wlog = logging.getLogger("werkzeug")
        wlog.setLevel(logging.WARNING)
        # If our logger has a parent, inherit its handlers for consistency
        if self.logger.parent:  # pragma: no cover
            for h in self.logger.parent.handlers:
                wlog.addHandler(h)

        # Automatically inject the Flask "app" variable into the calling module's global namespace
        # for compatibility with WSGI servers like gunicorn.
        #
        # This mechanism allows plugin developers to simply instantiate a CluePlugin without
        # needing to explicitly expose the underlying Flask app. WSGI servers typically expect
        # to find an 'app' variable in the module's global scope when using module:variable
        # syntax (e.g., "mymodule:app").
        #
        # Example usage in a plugin module:
        #   plugin = CluePlugin("my-plugin", ...)
        #   # The 'app' variable is now automatically available for gunicorn
        #   # Command: gunicorn mymodule:app
        current_frame = inspect.currentframe()
        if current_frame:
            caller_frame = current_frame.f_back
            if caller_frame and "app" not in caller_frame.f_globals:
                caller_frame.f_globals["app"] = self.app

        self.logger.debug("Initialization complete!")

    def __check_actions(self) -> list[Action] | None:
        """Validate token and retrieve dynamic actions if setup_actions is configured.

        This method handles token validation when required and calls the setup_actions
        function to get a potentially user-specific or dynamically generated list of actions.

        Returns:
            list[Action] | None: List of actions if setup_actions is configured, None otherwise

        Raises:
            AuthenticationException: If token validation fails
        """
        if self.setup_actions:
            # Validate token if token validation is configured
            if self.validate_token:
                token, error = self.validate_token()

                if error:
                    self.logger.error("Error on token validation: %s", error)
                    raise AuthenticationException(error)
            else:
                token = None

            # Call user-defined setup_actions with base actions and validated token
            return self.setup_actions(self.actions or [], token)

        return None

    def __init_apm(self):
        """Initialize Application Performance Monitoring (APM) using Elastic APM.

        Sets up ElasticAPM integration with Flask if APM_SERVER_URL environment
        variable is configured. This enables automatic collection of performance
        metrics, error tracking, and distributed tracing.

        Environment Variables:
            APM_SERVER_URL: URL of the Elastic APM server to send metrics to
        """
        # Check if APM server URL is configured via environment variable
        apm_server_url = os.environ.get("APM_SERVER_URL")
        if apm_server_url is None:
            return

        self.logger.debug("Initializing APM")

        # Import ElasticAPM components (lazy import to avoid dependency issues)
        import elasticapm
        from elasticapm.contrib.flask import ElasticAPM

        self.logger.info(f"Exporting application metrics to: {apm_server_url}")

        # Initialize ElasticAPM with Flask app and configure client
        ElasticAPM(self.app, client=elasticapm.Client(server_url=apm_server_url, service_name=self.app_name))

    def __build_ctx(self):
        """Create a context wrapper function for preserving Flask request context in greenlets.

        Flask request context is thread-local and doesn't automatically propagate to
        greenlets. This function captures the current request context and returns a
        wrapper that pushes it into each greenlet before execution.

        Returns:
            Callable: A wrapper function that preserves Flask context and handles exceptions
        """
        # Capture the current Flask request context to propagate to greenlets
        current_req_ctx = _cv_request.get(None)
        reqctx = current_req_ctx.copy() if current_req_ctx else None

        def wrap_ctx(func: Callable, *args: Any, **kwargs) -> tuple[Any, Exception | None]:
            """Wrapper that pushes Flask context and handles enrichment function execution.

            Args:
                func: The enrichment function to execute
                *args: Arguments to pass to the function
                **kwargs: Keyword arguments to pass to the function

            Returns:
                tuple[Any, Exception | None]: (result, exception) tuple
            """
            # Push the request context into this greenlet's scope
            if reqctx:
                reqctx.push()

            try:
                self.logger.debug("Executing enrichment function")
                return func(*args, **kwargs), None
            except NotFoundException:
                # NotFoundException means no results found - return empty list, not an error
                self.logger.warning("NotFoundException thrown in greenlet")
                return [], None
            except ClueException as e:
                # Other Clue exceptions should be propagated as errors
                self.logger.exception("ClueException thrown in greenlet")
                return None, e

        return wrap_ctx

    def __default_bulk_lookup(  # noqa: C901
        self: Self,
        bulk_result: dict[str, dict[str, BulkEntry]],
        items: list[dict[str, str]],
        params: Params,
        token: str | None,
    ):
        """Default bulk lookup implementation using greenlets for concurrent enrichment.

        This method processes multiple enrichment requests concurrently by spawning
        greenlets (lightweight threads) for each item. It uses the single-item enrich
        function to process each request while maintaining Flask request context. Note
        that this may lead to inefficient lookups (e.g. making ten requests to a database,
        instead of a single bulk query)

        Args:
            bulk_result: Dictionary to populate with results, keyed by type then value
            items: List of items to enrich, each containing 'type' and 'value' keys
            params: Request parameters including timeouts and limits
            token: Authentication token to pass to enrichment functions
        """
        self.logger.debug("Using default bulk lookup")

        # Create context wrapper to preserve Flask request context in greenlets
        wrap_ctx = self.__build_ctx()
        # Limit pool size to prevent resource exhaustion: min(items, cpu_count * 5 + 4)
        thread_pool = gevent.pool.Pool(min(len(items), (os.cpu_count() or 0) * 5 + 4))
        greenlets: list[tuple[str, str, Greenlet]] = []

        # Spawn a greenlet for each enrichment request
        for entry in items:
            # Store type, value, and greenlet for later result processing
            greenlets.append(
                (
                    entry["type"],
                    entry["value"],
                    thread_pool.spawn(
                        wrap_ctx,  # Context wrapper function
                        self.enrich,  # User's enrichment function
                        entry["type"],  # Selector type
                        entry["value"],  # Selector value
                        params,  # Request parameters
                        token,  # Authentication token
                    ),
                )
            )

        # Calculate remaining time until deadline
        timeout = params.deadline + params.max_timeout - time.time()
        self.logger.debug("Joining threadpool (timeout=%s)", timeout)

        # Wait for all greenlets to complete or timeout
        thread_pool.join(timeout=timeout)

        # Process results from all completed greenlets
        for type_name, value, greenlet in greenlets:
            greenlet_result = greenlet.value

            # Check if greenlet completed successfully with results
            if greenlet_result is not None and greenlet_result[0] is not None:
                results: Union[list[QueryEntry], QueryEntry] = greenlet_result[0]
                # Ensure results is always a list for consistent handling
                if not isinstance(results, list):
                    results = [results]

                bulk_result[type_name][value] = BulkEntry(items=results)

                # Cache successful results if caching is enabled
                if self.cache:
                    self.logger.info("Caching results for selector %s:%s", type_name, value)
                    try:
                        self.cache.set(type_name, value, params, results)
                    except KeyError:
                        self.logger.warning("Selector not present in bulk result, skipping cache step")
            else:
                # Handle errors: timeout, exceptions, or other failures
                error = "Request Timed Out"
                if greenlet_result is not None and greenlet_result[1] is not None:
                    error = str(greenlet_result[1])

                # Use greenlet exception if available, otherwise use our error message
                bulk_result[type_name][value] = BulkEntry(
                    error=(error if not greenlet.exception else str(greenlet.exception))
                )

        self.logger.debug(
            "Completing bulk lookup (%s threads remaining)",
            len(list(not greenlet[2].dead for greenlet in greenlets)),
        )

    def __init_routes(self):
        """Set up all Flask routes for the plugin API endpoints.

        Registers the following endpoints:
        - GET /actions/: List available actions
        - POST /actions/<action_id>/: Execute a specific action
        - GET /fetchers/: List available fetchers
        - POST /fetchers/<fetcher_id>: Execute a specific fetcher
        - GET /types/: List supported types
        - GET /lookup/<type_name>/<value>/: Single enrichment lookup
        - POST /lookup/: Bulk enrichment lookup
        - GET /healthz/live: Liveness probe
        - GET /healthz/ready: Readiness probe
        """
        self.logger.debug("Initializing routes")

        self.app.add_url_rule("/actions/", self.get_actions.__name__, self.get_actions, methods=["GET"])
        self.app.add_url_rule(
            "/actions/<action_id>/", self.execute_action.__name__, self.execute_action, methods=["POST"]
        )
        self.app.add_url_rule("/fetchers/", self.get_fetchers.__name__, self.get_fetchers, methods=["GET"])
        self.app.add_url_rule(
            "/fetchers/<fetcher_id>", self.execute_fetcher.__name__, self.execute_fetcher, methods=["POST"]
        )
        self.app.add_url_rule("/types/", self.get_type_names.__name__, self.get_type_names, methods=["GET"])
        self.app.add_url_rule("/lookup/<type_name>/<value>/", self.lookup.__name__, self.lookup, methods=["GET"])
        self.app.add_url_rule("/lookup/", self.bulk_lookup.__name__, self.bulk_lookup, methods=["POST"])
        self.app.add_url_rule("/healthz/live", self.liveness.__name__, self.liveness)
        self.app.add_url_rule("/healthz/ready", self.readyness.__name__, self.readyness)

    def make_api_response(self: Self, data: Any, err: str = "", status_code: int = 200) -> Response:
        """Create a standardized JSON response for all API endpoints.

        This method ensures consistent response format across all plugin endpoints,
        handles automatic error extraction from result objects, and logs all requests.

        Args:
            data: The response data (will be JSON serialized)
            err: Error message (if any)
            status_code: HTTP status code (default: 200)

        Returns:
            Response: Flask response with standardized JSON structure

        Response Format:
            {
                "api_response": <data>,
                "api_error_message": <error_string>,
                "api_status_code": <status_code>
            }
        """
        # Extract error messages from specialized result objects
        if isinstance(data, FetcherResult) and data.outcome == "failure" and not err:
            err = data.error or err

        if isinstance(data, ActionResult) and data.outcome == "failure" and not err:
            err = data.summary or err

        # Convert Pydantic models to dict for JSON serialization
        if isinstance(data, BaseModel):
            data = data.model_dump(mode="json", exclude_none=True)

        # Log all API requests with method, path, status, and error (if any)
        self.logger.info("%s %s - %s%s", request.method, request.path, status_code, f": {err}" if err else "")

        return make_response(
            jsonify(
                {
                    "api_response": data,
                    "api_error_message": err,
                    "api_status_code": status_code,
                }
            ),
            status_code,
        )

    def get_type_names(self: Self) -> Response:
        """Return the list of supported selector types with their classifications.

        Returns:
            Response: JSON response mapping each supported type to its classification level

        Response Format:
            {
                "type1": "classification_level",
                "type2": "classification_level",
                ...
            }
        """
        return self.make_api_response({tname: self.classification for tname in sorted(self.supported_types or [])})

    def lookup(self: Self, type_name: str, value: str) -> Response:  # noqa: C901
        """Run a lookup on a single type/value.

        Variables:
        type_name => Type to look up in the external system.
        value => Value to lookup. *Must be double URL encoded.*

        Query Params:
        max_timeout => Maximum execution time for the call in seconds
        limit       => Maximum number of items to return
        no_annotation      => If specified, do not return the annotation data
        include_raw        => Include raw data

        Returns:
        # List of:
        [
            {
                "count": <count of results from the external system>,
                "link": <url to search results in external system>,
                "classification": <access control>,    # Classification of the returned data
                "annotation": [
                    <Annotation entries >
                ]
            },
            ...,
        ]
        """
        if not self.enrich or not self.supported_types:
            return self.make_api_response({}, err="Enrichment is not supported by this plugin.", status_code=400)

        # Normalize generic "ip" type to specific "ipv4" or "ipv6" based on address format
        if type_name == "ip":
            is_ipv4 = isinstance(ipaddress.ip_address(value), ipaddress.IPv4Address)
            type_name = "ipv4" if is_ipv4 else "ipv6"

        try:
            params = Params.from_request()
        except RuntimeError as e:
            self.logger.exception("Error on params parsing.")

            return self.make_api_response(None, str(e), 504)

        # Double URL decode the value (required by API specification)
        value = ul.unquote(ul.unquote(value))
        # Validate that the requested type is supported by this plugin
        if type_name not in self.supported_types:
            return self.make_api_response(
                None,
                f"Invalid type name: {type_name} [Valid types: {', '.join(self.supported_types)}].",
                422,
            )

        token: str | None = None
        if self.validate_token:
            token, error = self.validate_token()

            if error:
                return self.make_api_response(None, f"Error on token validation: {error}", status_code=401)
        try:
            if self.cache and params.use_cache:
                if result := self.cache.get(type_name, value, params):
                    self.logger.debug("Cache hit")

                    return self.make_api_response(
                        TypeAdapter(list[QueryEntry]).dump_python(result, mode="json", exclude_none=True),
                        status_code=200,
                    )
                else:
                    self.logger.debug("Cache miss")
        except Exception:
            self.logger.exception("Unknown internal exception on cache check, continuing to standard enrichment")

        try:
            results = self.enrich(type_name, value, params, token)

            if not isinstance(results, list):
                results = [results]
        except InvalidDataException as e:
            return self.make_api_response(None, e.message, 400)
        except NotFoundException:
            return self.make_api_response([], "", 404)
        except TimeoutException as e:
            return self.make_api_response(None, e.message or "Request timed out", 408)
        except UnprocessableException as e:
            return self.make_api_response(None, e.message, 422)
        except Exception as e:
            self.logger.exception("Unknown internal exception")
            return self.make_api_response(None, f"Something went wrong when enriching: {e}", 500)

        if self.cache:
            self.cache.set(type_name, value, params, results)

        return self.make_api_response(
            TypeAdapter(list[QueryEntry]).dump_python(results, mode="json", exclude_none=True),
            status_code=200,
        )

    def bulk_lookup(self: Self) -> Response:  # noqa: C901
        """This is the default bulk support for Clue plugins.

        It is a wrapper on top of the single item route that will use a threadpool to perform the
        request simultaneously.

        Variables:
        None

        Query Params:
        max_timeout     => Maximum execution time for the call in seconds
        limit           => Maximum number of items to return
        no_annotation   => If specified, do not return the annotation data
        include_raw     => Include raw data
        deadline        => The POSIX timestamp the plugin should aim to return by

        Data Block:
        [
            {"type": "ip", "value": "127.0.0.1"},
            ...
        ]

        Returns:
        {                           # Dictionary of data source queried
            "ip": {
                "127.0.0.1":{
                    "error": null,          # Error message returned by data source
                    "items": [              # list of results from the source
                            ...,
                    ],

                },
                ...
            },
            ...
        }
        """
        if not (self.enrich or self.alternate_bulk_lookup) or not self.supported_types:
            return self.make_api_response({}, err="Bulk enrichment is not supported by this plugin.", status_code=400)

        try:
            params = Params.from_request()
        except RuntimeError as e:
            return self.make_api_response(None, str(e), 504)

        # Get and validate POST data
        post_data = request.json
        if not isinstance(post_data, list):
            return self.make_api_response(None, "Request data is not in the correct format", 422)

        self.logger.info(f"Starting bulk lookup on {len(post_data)} entries")
        bulk_result: dict[str, dict[str, BulkEntry]] = {}

        remaining_items: list[dict[str, str]] = []
        "Valid, non-cached items that must be enriched"

        for entry in post_data:
            if "type" not in entry or "value" not in entry:
                return self.make_api_response(None, "Request data is not in the correct format", 422)

            type_name = entry["type"]
            bulk_result.setdefault(type_name, {})
            if type_name not in self.supported_types:
                self.logger.warning("Invalid type name provided: %s", type_name)

                bulk_result[entry["type"]][entry["value"]] = BulkEntry(
                    error=f"Invalid type name: {type_name}. [valid types: {', '.join(self.supported_types)}]"
                )
                continue

            try:
                if self.cache and params.use_cache:
                    if result := self.cache.get(entry["type"], entry["value"], params):
                        self.logger.debug("Cache hit")

                        bulk_result[entry["type"]][entry["value"]] = BulkEntry(items=result)
                        continue
                    else:
                        self.logger.debug("Cache miss")
            except Exception:
                self.logger.exception("Exception on caching - continuing to execution")

            remaining_items.append(entry)

        token: str | None = None
        if self.validate_token:
            if self.logger:
                self.logger.debug("Executing plugin-provided token validator")

            token, error = self.validate_token()

            if error:
                return self.make_api_response(None, f"Error on token validation: {error}", status_code=401)

            if self.logger:
                self.logger.debug("Token is valid")
        else:
            if self.logger:
                self.logger.debug("No token validator provided")

        # All results were cached
        if len(remaining_items) == 0:
            if self.logger:
                self.logger.info("All values retrieved from cache")
        # Alternate bulk lookup is provided
        elif self.alternate_bulk_lookup:
            if self.logger:
                self.logger.debug("Executing plugin-provided alternate bulk lookup script")

            try:
                alternate_results = self.alternate_bulk_lookup(remaining_items, params)

                for _type, _values in alternate_results.items():
                    for _value, _result in _values.items():
                        bulk_result[_type][_value] = _result
            except InvalidDataException as e:
                return self.make_api_response(None, e.message, 400)
            except NotFoundException:
                return self.make_api_response([], "", 404)
            except TimeoutException as e:
                return self.make_api_response(None, e.message or "Request timed out", 408)
            except UnprocessableException as e:
                return self.make_api_response(None, e.message, 422)
            except Exception as e:
                if self.logger:
                    self.logger.exception("Unknown internal exception")
                return self.make_api_response(None, f"Something went wrong when enriching: {e}", 500)

            if self.cache and len(remaining_items) > 0:
                if self.logger:
                    self.logger.info("Caching results for %s selectors", len(remaining_items))

                for entry in remaining_items:
                    try:
                        items = bulk_result[entry["type"]][entry["value"]].items
                        self.cache.set(entry["type"], entry["value"], params, items)
                    except KeyError:
                        if self.logger:
                            self.logger.warning("Selector not present in bulk result, skipping cache step")
        # Default bulk lookup
        else:
            self.__default_bulk_lookup(bulk_result, remaining_items, params, token)

        # Calculate how close we came to the deadline (positive = time remaining, negative = overrun)
        variance = params.deadline - time.time()

        if self.logger:
            if variance < 0:
                self.logger.warning(f"Deadline missed by {-round(variance * 1000)}ms")
            else:
                self.logger.debug(f"Deadline met, {round(variance * 1000)}ms to spare")

        return self.make_api_response(
            TypeAdapter(dict[str, dict[str, BulkEntry]]).dump_python(bulk_result, mode="json", exclude_none=True)
        )

    def get_actions(self: Self) -> Response:
        """Gets all the possible actions for this plugin.

        Variables:
        None

        Returns:
        {                           # Dictionary of actions
            "action1": {
                ...                 # schema of the action
            },
            ...
        }
        """
        try:
            actions = self.__check_actions()
        except Exception:
            self.logger.exception("Exception on setup actions:")

            return self.make_api_response({}, err="Error on action setup.", status_code=500)

        if actions is None:
            actions = self.actions or []

        if not self.validate_token or not (token := self.validate_token()[0]):
            self.logger.debug("Returning %s actions for unknown user", len(actions))
        else:
            self.logger.debug("Returning %s actions for user %s", len(actions), get_username(token))

        results: dict[str, dict[str, Any]] = {}
        for action in actions:
            # Extract base action fields (id, name, description, etc.)
            schema = action.model_dump(mode="json", include=set(ActionBase.model_fields.keys()), exclude_none=True)
            # Generate JSON schema for the action's parameter type
            schema["params"] = cast(
                BaseModel, cast(type[Any], action.model_fields["params"].annotation).__args__[0]
            ).model_json_schema()

            # Convert to ActionSpec format and add to results
            results[action.id] = ActionSpec.model_validate(schema).model_dump(mode="json", exclude_none=True)

        return self.make_api_response(results)

    def execute_action(self: Self, action_id: str):  # noqa: C901
        """Executes the specified action.

        Args:
            action_id (str): The ID of the action to execute

        Returns:
            Response: A Response object with an ActionResult as the body.
        """
        if not self.run_action:
            return self.make_api_response({}, err=f"{self.app_name} does not support any actions.", status_code=400)

        try:
            actions = self.__check_actions()
        except Exception:
            self.logger.exception("Exception on setup actions:")

            return self.make_api_response({}, err="Error on action setup.", status_code=500)

        if actions is None:
            actions = self.actions or []

        action_to_run = next((action for action in actions if action.id == action_id), None)
        if not action_to_run:
            return self.make_api_response({}, err="Action does not exist", status_code=404)

        token: str | None = None
        if self.validate_token:
            self.logger.debug("Executing plugin-provided token validator")

            token, error = self.validate_token()

            if error:
                return self.make_api_response(None, f"Error on token validation: {error}", status_code=401)

            self.logger.debug("Token is valid")
        else:
            self.logger.warning("No token validation provided. The access token will not be provided to the action.")

        # Extract the parameter type from the action definition for validation
        param_type: Any = action_to_run.model_fields["params"].annotation or Any

        try:
            raw_request = request.json
            if not raw_request:
                self.logger.warning("No request body specified.")

                return self.make_api_response(ActionResult(outcome="failure", summary="No request body specified."))

            # Validate request body against the action's parameter schema
            action_request: ExecuteRequest = TypeAdapter(param_type.__args__[0]).validate_python(
                raw_request, context={"action": action_to_run}
            )

            self.logger.info(
                "Executing Action '%s' on %s selectors",
                action_id,
                len(action_request.selectors) if action_request.selectors else 1,
            )

            result = self.run_action(action_to_run, action_request, token)
        except json.JSONDecodeError as e:
            self.logger.warning("JSON decoding error during execution: %s", str(e))

            result = ActionResult(
                outcome="failure",
                summary=f"Invalid request format. Request body must be valid JSON. Error: {str(e)}",
            )
        except ValidationError as err:
            self.logger.warning("Validation error during execution: %s", str(err))

            result = ActionResult(outcome="failure", summary=f"Validation error on execution: {str(err)}")
        except ClueException as e:
            self.logger.exception("ClueException during execution:")

            result = ActionResult(outcome="failure", summary=f"Error encountered during execution: {e.message}")
        except Exception as e:
            self.logger.exception("%s during execution:", e.__class__.__name__)

            result = ActionResult(outcome="failure", summary=f"An unknown error occurred during execution: {str(e)}")
        finally:
            self.logger.info("Execution finished.")

        self.logger.info("Action result: %s", result.outcome)

        return self.make_api_response(result)

    def get_fetchers(self: Self) -> Response:
        """Get all available fetchers for this plugin.

        Returns a dictionary of fetcher definitions, each containing the fetcher's
        schema including supported types, output format, and other metadata.

        Returns:
            Response: JSON response containing fetcher definitions

        Response Format:
            {
                "fetcher1": {
                    "id": "fetcher1",
                    "name": "Fetcher Name",
                    "description": "Description",
                    "supported_types": ["type1", "type2"],
                    "output_format": "format",
                    ...
                },
                ...
            }
        """
        if not self.fetchers:
            self.logger.debug("No fetchers to show")
            return self.make_api_response({})

        results: dict[str, dict[str, Any]] = {}
        for fetcher in self.fetchers:
            # Serialize fetcher definition to JSON-compatible dict
            schema = fetcher.model_dump(mode="json", exclude_none=True)
            results[fetcher.id] = schema

        return self.make_api_response(results)

    def execute_fetcher(self: Self, fetcher_id: str):  # noqa: C901
        """Runs the specified fetcher.

        Args:
            fetcher_id (str): The ID of the fetcher to execute

        Returns:
            Response: A Response object with a FetcherResult as the body.
        """
        if not self.run_fetcher or not self.fetchers:
            return self.make_api_response({}, err=f"{self.app_name} does not support any fetchers.", status_code=400)

        # Find the requested fetcher by ID
        fetcher_to_run = next((fetcher for fetcher in self.fetchers if fetcher.id == fetcher_id), None)
        if not fetcher_to_run:
            return self.make_api_response({}, err=f"Fetcher {fetcher_id} does not exist", status_code=404)

        token: str | None = None
        if self.validate_token:
            self.logger.debug("Executing plugin-provided token validator")

            token, error = self.validate_token()

            if error:
                return self.make_api_response(None, f"Error on token validation: {error}", status_code=401)

            self.logger.debug("Token is valid")

        status_code = 200
        try:
            if not request.json:
                return self.make_api_response(
                    FetcherResult(outcome="failure", format="error", error="No request body specified."),
                    status_code=400,
                )

            # Validate request body as a Selector object
            raw_request = Selector.model_validate(request.json)

            self.logger.info("Running fetcher '%s'", fetcher_id)

            result = self.run_fetcher(fetcher_to_run, raw_request, token)
        except json.JSONDecodeError as e:
            self.logger.warning("JSON decoding error during execution: %s", str(e))

            status_code = 400
            result = FetcherResult(
                outcome="failure",
                format="error",
                error=f"Invalid request format. Request body must be valid JSON. Error: {str(e)}",
            )
        except ValidationError as err:
            self.logger.warning("Validation error during execution: %s", str(err))

            status_code = 400
            result = FetcherResult(outcome="failure", format="error", error=str(err))
        except ClueException as e:
            self.logger.exception("ClueException during execution:")

            status_code = 500
            result = FetcherResult(
                outcome="failure", format="error", error=f"Error encountered during execution: {e.message}"
            )
        except Exception as e:
            self.logger.exception("%s during execution:", e.__class__.__name__)

            status_code = 500
            result = FetcherResult(
                outcome="failure", format="error", error=f"An unknown error occurred during execution: {str(e)}"
            )
        finally:
            self.logger.info("Fetcher completed.")

        self.logger.info("Fetcher outcome: %s", result.outcome)

        if result.error:
            self.logger.info("Error Message: %s", result.error)

        return self.make_api_response(result, status_code=status_code)

    def use(self, func: Callable):
        """Register a function to be used by the CluePlugin for specific operations.

        This decorator allows you to register functions that will be called during various
        plugin operations. The function name must match one of the supported overridable
        functions defined in OVERRIDABLE_FUNCTIONS.

        Supported function names and their purposes:
            - enrich: Main enrichment function for processing selectors
            - alternate_bulk_lookup: Alternative bulk enrichment implementation
            - liveness: Kubernetes liveness probe endpoint
            - readyness: Kubernetes readiness probe endpoint
            - run_action: Function to execute plugin actions
            - run_fetcher: Function to execute plugin fetchers
            - setup_actions: Runtime action definition generation
            - validate_token: Custom authentication token validation

        Args:
            func: The function to register. The function name determines which plugin
                  operation it will be used for.

        Returns:
            The original function (allows use as a decorator).

        Example:
            ```python
            plugin = CluePlugin("my_plugin")

            @plugin.use
            def enrich(type_name: str, value: str, params: Params, token: str | None):
                # Your enrichment logic here
                return QueryEntry(...)
            ```

        Note:
            If a function with the same name is already registered, a warning will be logged
            and the new function will replace the existing one.
        """
        function_name = func.__name__
        if function_name not in OVERRIDABLE_FUNCTIONS:
            self.logger.error(
                "%s is not a valid function to use in a clue plugin. Supported list: %s",
                function_name,
                ", ".join(OVERRIDABLE_FUNCTIONS),
            )

        # Warn if overwriting an existing function
        if getattr(self, function_name) is not None:
            self.logger.warning("plugin.uses decorator is overwriting existing function: %s", function_name)

        # Dynamically set the function as an attribute of this plugin instance
        setattr(self, function_name, func)

        return func
