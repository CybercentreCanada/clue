import type { BlockDefinition } from '../types';

export const BLOCK_DEFINITIONS: BlockDefinition[] = [
  // ── Setup & Scaffold ──────────────────────────────────────────
  {
    id: 'setup.plugin_init',
    label: 'Plugin Initialisation',
    category: 'Setup',
    icon: 'settings',
    description: 'Initialise a CluePlugin with supported types, classification, and caching.',
    configFields: [
      { key: 'app_name', label: 'App Name', type: 'text', defaultValue: 'my-plugin' },
      {
        key: 'classification',
        label: 'Classification',
        type: 'select',
        options: ['TLP:CLEAR', 'TLP:GREEN', 'TLP:AMBER', 'TLP:RED'],
        defaultValue: 'TLP:CLEAR'
      },
      {
        key: 'supported_types',
        label: 'Supported Types (comma-separated)',
        type: 'text',
        defaultValue: 'domain,ipv4,url'
      },
      { key: 'enable_cache', label: 'Enable Cache', type: 'boolean', defaultValue: true }
    ],
    code: `import os
from clue.plugin import CluePlugin
from clue.common.log import get_logger

logger = get_logger(__file__)
CLASSIFICATION = os.environ.get("CLASSIFICATION", "{{classification}}")

plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "{{app_name}}"),
    classification=CLASSIFICATION,
    supported_types={ {{supported_types}} },
    enable_cache={{enable_cache}},
    logger=logger,
)`
  },
  {
    id: 'setup.env_vars',
    label: 'Environment Variables',
    category: 'Setup',
    icon: 'tune',
    description: 'Read configuration from environment variables with defaults.',
    configFields: [
      {
        key: 'vars',
        label: 'Variables (NAME=default, one per line)',
        type: 'text',
        defaultValue: 'API_URL=https://example.com/api\nAPI_KEY=\nVERIFY=true'
      }
    ],
    code: `import os

{{vars}}`
  },
  {
    id: 'setup.imports',
    label: 'Common Imports',
    category: 'Setup',
    icon: 'inventory_2',
    description: 'Standard imports used in most Clue plugins.',
    configFields: [
      { key: 'include_pydantic', label: 'Include Pydantic', type: 'boolean', defaultValue: true },
      { key: 'include_datetime', label: 'Include datetime', type: 'boolean', defaultValue: false }
    ],
    code: `import os
import requests
from pydantic_core import Url
from clue.common.log import get_logger
from clue.common.exceptions import TimeoutException, NotFoundException, InvalidDataException
from clue.plugin.models import Annotation, Params, QueryEntry`
  },

  // ── HTTP Requests ──────────────────────────────────────────────
  {
    id: 'http.get_request',
    label: 'HTTP GET Request',
    category: 'HTTP',
    icon: 'cloud_download',
    description: 'Make an authenticated GET request with error handling and timeout.',
    configFields: [
      { key: 'url_expr', label: 'URL expression', type: 'text', defaultValue: 'f"{API_URL}/endpoint/{value}"' },
      { key: 'auth_header', label: 'Auth header name', type: 'text', defaultValue: 'x-apikey' },
      { key: 'auth_value', label: 'Auth value expression', type: 'text', defaultValue: 'API_KEY' },
      { key: 'verify_ssl', label: 'Verify SSL', type: 'boolean', defaultValue: true }
    ],
    code: `session = requests.Session()
headers = {
    "accept": "application/json",
    "{{auth_header}}": {{auth_value}},
}

try:
    response = session.get(
        {{url_expr}},
        headers=headers,
        timeout=params.max_timeout,
        verify={{verify_ssl}},
    )
except requests.exceptions.Timeout as e:
    raise TimeoutException("Service timed out", cause=e)

if response.status_code == 404:
    raise NotFoundException(f"No results found for {value}")
elif response.status_code != 200:
    raise InvalidDataException(f"Unexpected status: {response.status_code}")

data = response.json()`
  },
  {
    id: 'http.post_request',
    label: 'HTTP POST Request',
    category: 'HTTP',
    icon: 'cloud_upload',
    description: 'Make a POST request with a JSON or form body.',
    configFields: [
      { key: 'url_expr', label: 'URL expression', type: 'text', defaultValue: 'f"{API_URL}/query"' },
      {
        key: 'body_format',
        label: 'Body format',
        type: 'select',
        options: ['json', 'form'],
        defaultValue: 'json'
      },
      { key: 'body_expr', label: 'Body expression', type: 'text', defaultValue: '{"query": value}' },
      { key: 'auth_header', label: 'Auth header name', type: 'text', defaultValue: 'Authorization' },
      { key: 'auth_value', label: 'Auth value expression', type: 'text', defaultValue: 'f"Bearer {token}"' }
    ],
    code: `session = requests.Session()
headers = {
    "accept": "application/json",
    "{{auth_header}}": {{auth_value}},
}

try:
    response = session.post(
        {{url_expr}},
        headers=headers,
        {{body_format}}={{body_expr}},
        timeout=params.max_timeout,
    )
except requests.exceptions.Timeout as e:
    raise TimeoutException("Service timed out", cause=e)

if response.status_code not in (200, 201):
    raise InvalidDataException(f"Unexpected status: {response.status_code}")

data = response.json()`
  },
  {
    id: 'http.bearer_token',
    label: 'Bearer Token Auth',
    category: 'HTTP',
    icon: 'vpn_key',
    description: 'Extract and validate the Bearer token from the incoming request.',
    configFields: [],
    code: `from flask import request as flask_request

token = flask_request.headers.get("Authorization", None, type=str)
if token:
    token = token.split()[1]  # "Bearer <token>"`
  },

  // ── Enrich Functions ───────────────────────────────────────────
  {
    id: 'enrich.basic',
    label: 'Enrich Function',
    category: 'Enrich',
    icon: 'functions',
    description: 'Register a basic enrich function with the plugin. Nest HTTP/result blocks inside.',
    isWrapper: true,
    configFields: [{ key: 'analytic_name', label: 'Analytic name', type: 'text', defaultValue: 'My Plugin' }],
    code: `@plugin.use
def enrich(type_name: str, value: str, params: Params, token: str | None) -> QueryEntry | None:
    """Enrich a single indicator."""`
  },
  {
    id: 'enrich.type_dispatch',
    label: 'Type Dispatch Enrich',
    category: 'Enrich',
    icon: 'alt_route',
    description: 'Enrich function that dispatches by indicator type. Nest If/Elif blocks for each type.',
    isWrapper: true,
    configFields: [],
    code: `@plugin.use
def enrich(type_name: str, value: str, params: Params, token: str | None) -> QueryEntry | None:
    """Route enrichment by indicator type."""`
  },
  {
    id: 'enrich.token_validation',
    label: 'Token Validation',
    category: 'Enrich',
    icon: 'verified_user',
    description: 'Register a validate_token function for OBO (On-Behalf-Of) authentication.',
    configFields: [{ key: 'audience', label: 'Expected audience', type: 'text', defaultValue: 'my-service' }],
    code: `import json
import base64

@plugin.use
def validate_token():
    """Validate the JWT Bearer token audience."""
    token = flask_request.headers.get("Authorization", None, type=str)
    if not token:
        return False
    token = token.split()[1]
    try:
        payload = json.loads(
            base64.b64decode(token.split(".")[1] + "==").decode()
        )
        return payload.get("aud") == "{{audience}}"
    except Exception:
        return False`
  },

  // ── Results & Annotations ──────────────────────────────────────
  {
    id: 'result.annotation',
    label: 'Build Annotation',
    category: 'Results',
    icon: 'label',
    description: 'Create a single Annotation with analytic name, type, value, and optional details.',
    configFields: [
      { key: 'analytic', label: 'Analytic name', type: 'text', defaultValue: 'My Plugin - Feature' },
      {
        key: 'ann_type',
        label: 'Annotation type',
        type: 'select',
        options: ['context', 'opinion', 'assessment'],
        defaultValue: 'context'
      }
    ],
    code: `annotation = Annotation(
    analytic="{{analytic}}",
    type="{{ann_type}}",
    value=result_value,
    summary=f"Summary for {value}",
    details=f"Detailed information about the finding",
    confidence=0.9,
)`
  },
  {
    id: 'result.query_entry',
    label: 'Build QueryEntry',
    category: 'Results',
    icon: 'output',
    description: 'Assemble a QueryEntry with classification, link, count, and annotations list.',
    configFields: [
      {
        key: 'link_template',
        label: 'Link URL template',
        type: 'text',
        defaultValue: 'f"https://example.com/search?q={value}"'
      }
    ],
    code: `result = QueryEntry(
    classification=CLASSIFICATION,
    link=Url({{link_template}}),
    count=len(annotations),
    annotations=annotations,
)`
  },
  {
    id: 'result.malice_verdict',
    label: 'Malice Verdict Logic',
    category: 'Results',
    icon: 'gavel',
    description: 'Determine malicious/suspicious/benign verdict from a numeric score.',
    configFields: [
      { key: 'malicious_threshold', label: 'Malicious threshold', type: 'text', defaultValue: '1000' },
      { key: 'suspicious_threshold', label: 'Suspicious threshold', type: 'text', defaultValue: '300' }
    ],
    code: `def determine_verdict(score: int) -> str:
    """Return a verdict string based on a numeric score."""
    if score >= {{malicious_threshold}}:
        return "malicious"
    elif score >= {{suspicious_threshold}}:
        return "suspicious"
    return "benign"`
  },

  // ── Actions & Fetchers ─────────────────────────────────────────
  {
    id: 'action.basic',
    label: 'Action Handler',
    category: 'Actions',
    icon: 'play_arrow',
    description: 'Register an action handler that the plugin can execute.',
    configFields: [{ key: 'action_id', label: 'Action ID', type: 'text', defaultValue: 'my_action' }],
    code: `from clue.plugin.models import Action, ActionResult, ExecuteRequest

@plugin.use
def run_action(action: Action, action_request: ExecuteRequest, token: str | None) -> ActionResult:
    """Handle an action invocation."""
    if action.id != "{{action_id}}":
        return ActionResult(outcome="failure", summary=f"Unknown action: {action.id}")

    value = action_request.selector.value
    # ... perform action logic ...

    return ActionResult(
        outcome="success",
        summary=f"Action {{action_id}} completed for {value}",
    )`
  },

  // ── Utility ────────────────────────────────────────────────────
  {
    id: 'util.logging',
    label: 'Logging',
    category: 'Utility',
    icon: 'terminal',
    description: 'Add structured log statements for debugging and monitoring.',
    configFields: [
      {
        key: 'level',
        label: 'Log level',
        type: 'select',
        options: ['debug', 'info', 'warning', 'error'],
        defaultValue: 'info'
      },
      { key: 'message', label: 'Log message', type: 'text', defaultValue: 'Processing {type_name}: {value}' }
    ],
    code: `logger.{{level}}("{{message}}")`
  },
  {
    id: 'util.retry',
    label: 'Retry with Backoff',
    category: 'Utility',
    icon: 'replay',
    description: 'Retry logic with exponential backoff for initialisation or flaky calls.',
    configFields: [
      { key: 'max_retries', label: 'Max retries', type: 'text', defaultValue: '10' },
      { key: 'base_delay', label: 'Base delay (s)', type: 'text', defaultValue: '1.0' }
    ],
    code: `import time

def initialize_with_retry(base_delay: float = {{base_delay}}, max_retries: int = {{max_retries}}):
    """Retry with exponential backoff."""
    attempt = 0
    client = None
    while client is None and attempt < max_retries:
        try:
            # ... initialisation attempt ...
            client = create_client()
        except Exception:
            delay = min(base_delay * (2 ** attempt), 60.0)
            logger.warning(f"Init failed, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
            attempt += 1
    if client is None:
        raise RuntimeError("Failed to initialise after retries")
    return client`
  },
  {
    id: 'util.url_parsing',
    label: 'URL / Domain Parsing',
    category: 'Utility',
    icon: 'link',
    description: 'Extract domain or encode URL for API lookups.',
    configFields: [],
    code: `from urllib.parse import urlsplit, quote
import base64

def extract_domain(value: str) -> str:
    """Extract the hostname from a URL, or return the value as-is for domains."""
    if value.startswith(("http://", "https://")):
        return urlsplit(value).hostname or value
    return value


def url_safe_encode(value: str) -> str:
    """Base64 URL-safe encode (VT-style)."""
    return base64.urlsafe_b64encode(value.encode()).decode().strip("=")`
  },
  {
    id: 'util.app_run',
    label: 'App Entry Point',
    category: 'Setup',
    icon: 'play_circle',
    description: 'The Flask app entry point that exposes the plugin.',
    configFields: [],
    code: `app = plugin.app`
  },

  // ── Control Flow ───────────────────────────────────────────────
  {
    id: 'flow.function',
    label: 'Function Definition',
    category: 'Control Flow',
    icon: 'segment',
    description: 'Wrap child blocks inside a Python function definition.',
    isWrapper: true,
    configFields: [
      { key: 'name', label: 'Function name', type: 'text', defaultValue: 'my_function' },
      { key: 'args', label: 'Arguments', type: 'text', defaultValue: 'value: str, params: Params' },
      { key: 'return_type', label: 'Return type (optional)', type: 'text', defaultValue: '' }
    ],
    code: `def {{name}}({{args}}){{return_type}}:`
  },
  {
    id: 'flow.if',
    label: 'If Statement',
    category: 'Control Flow',
    icon: 'call_split',
    description: 'Wrap child blocks inside an if-condition.',
    isWrapper: true,
    configFields: [{ key: 'condition', label: 'Condition', type: 'text', defaultValue: 'type_name == "ipv4"' }],
    code: `if {{condition}}:`
  },
  {
    id: 'flow.elif',
    label: 'Elif Clause',
    category: 'Control Flow',
    icon: 'call_split',
    description: 'Add an elif clause — usually placed after an If block.',
    isWrapper: true,
    configFields: [{ key: 'condition', label: 'Condition', type: 'text', defaultValue: 'type_name == "domain"' }],
    code: `elif {{condition}}:`
  },
  {
    id: 'flow.else',
    label: 'Else Clause',
    category: 'Control Flow',
    icon: 'call_split',
    description: 'Add an else clause — placed after an If or Elif block.',
    isWrapper: true,
    configFields: [],
    code: `else:`
  },
  {
    id: 'flow.try',
    label: 'Try Block',
    category: 'Control Flow',
    icon: 'shield',
    description: 'Wrap child blocks inside a try statement.',
    isWrapper: true,
    configFields: [],
    code: `try:`
  },
  {
    id: 'flow.except',
    label: 'Except Handler',
    category: 'Control Flow',
    icon: 'shield',
    description: 'Handle an exception — placed after a Try block.',
    isWrapper: true,
    configFields: [{ key: 'exception', label: 'Exception type', type: 'text', defaultValue: 'Exception as e' }],
    code: `except {{exception}}:`
  },
  {
    id: 'flow.for',
    label: 'For Loop',
    category: 'Control Flow',
    icon: 'loop',
    description: 'Iterate over a collection.',
    isWrapper: true,
    configFields: [
      { key: 'target', label: 'Loop variable', type: 'text', defaultValue: 'item' },
      { key: 'iterable', label: 'Iterable', type: 'text', defaultValue: 'results' }
    ],
    code: `for {{target}} in {{iterable}}:`
  },
  {
    id: 'flow.with',
    label: 'With Statement',
    category: 'Control Flow',
    icon: 'lock_open',
    description: 'Context manager — e.g. for OBO token injection.',
    isWrapper: true,
    configFields: [{ key: 'expr', label: 'Context expression', type: 'text', defaultValue: 'inject_al_token()' }],
    code: `with {{expr}}:`
  }
];

export const CATEGORY_COLORS: Record<string, string> = {
  Setup: '#43a047',
  HTTP: '#1e88e5',
  Enrich: '#fb8c00',
  Results: '#8e24aa',
  Actions: '#e53935',
  Utility: '#757575',
  'Control Flow': '#00897b'
};
