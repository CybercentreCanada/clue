"""$PLUGIN_TITLE

Team: $TEAM

Point of Contact: $CONTACT

Status: In Development

$DESCRIPTION
"""

import os

from clue.common.logging import get_logger
from clue.plugin import CluePlugin

# ---

# Classification level for this plugin - determines which selectors it can process
# Enrichment requests exceeding this classification level will not be processed
# Can be overridden via CLASSIFICATION environment variable, defaults to TLP:CLEAR
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")

# Initialize logger with standard Clue formatting for consistent logging across plugins
# This logger will be used internally by the CluePlugin for debug/info/error messages
logger = get_logger(__file__)

# Create the main CluePlugin instance that handles all server functionality
# This sets up the Flask app, routing, caching, and other core plugin infrastructure
plugin = CluePlugin(
    # App name used for logging and cache configuration - can be overridden via environment
    app_name=os.environ.get("APP_NAME", "$PLUGIN_NAME"),
    # Classification level that controls which selectors this plugin can enrich
    classification=CLASSIFICATION,
    # Comma-separated list of selector types this plugin supports (e.g., "ip,domain,hash")
    supported_types="$SUPPORTED_TYPES",
    # Logger instance for consistent formatting and debug output
    logger=logger,
)
