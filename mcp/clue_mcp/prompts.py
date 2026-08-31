import logging

logger = logging.getLogger(__name__)


def register_prompts(mcp):
    # ------------ action.py ------------
    # path : "action/"; variable : None
    @mcp.prompt(name="get_actions")
    def get_actions_prompt() -> str:
        return """Return the supported actions of each external service.

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of sources with their supported actions.
        <source_id>.<action_id>: {
            "id": "",
            "name": "",
            "classification": "",
            "summary": "",
            "supported_types": "",
            "params": {
                <JSON schema>
            }
        },
        ...,
    }
    """
    # action/<plugin_id>/<action_id>/status/<task_id>
    @mcp.prompt(name="execute_action")
    def get_execute_action_prompt() -> str:
        return"""Search other services for additional information related to the provided data.

    Variables:
    plugin_id (str): the ID of the plugin who owns the action to execute
    action_id (str): the ID of the action to execute

    Arguments:
    None

    Data Block:
    {
        type: "ip",
        value: "127.0.0.1",
        ...
    }

    Result Example:
    {
        "outcome": "success | failure", # was this execution a success or failure?
        "format": "link", # What format is the output in?
        "output": "http://example.com" # The output of the action. Can be any data structure.
    }
    """
    # action/<plugin_id>/<action_id>/status/<task_id>
    @mcp.prompt(name="get_action_status")
    def get_action_status_prompt() -> str :
        return """Get the status or result of a running action.

    Variables:
    plugin_id (str): the ID of the plugin who owns the action to execute
    action_id (str): the ID of the action to execute
    task_id (str): the ID of the specific task to get the status of

    Arguments:
    None


    Result Example:
    {
        "outcome": "success | failure | pending", # was this execution a success or failure or is it still pending?
        "format": "link", # What format is the output in?
        "output": "http://example.com" # The output of the action. Can be any data structure.
        "task_id": if the action is still running, what is the task id so that we can fetch the status again
    }
    """

# ----- fetcher.py -----
    # fetcher/
    @mcp.prompt(name="get_fetchers")
    def get_fetchers_prompt() -> str : 
        return """Return the supported fetchers of each external service.

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of sources with their supported fetchers.
        <source_id>.<fetcher_id>: {
            "id": "<fetcher_id>",
            "classification": "",
            "description": "",
            "format": ""
            "supported_types": ["ip", ...]
        },
        ...,
    }
    """

    # fetcher/<plugin_id>/<fetcher_id>
    @mcp.prompt("run_fetcher")
    def run_fetcher_prompt() -> str: 
        return """Search other services for additional information related to the provided data.

    Variables:
    plugin_id (str): the ID of the plugin who owns the action to execute
    fetcher_id (str): the ID of the action to execute

    Arguments:
    None

    Data Block:
    {
        type: "ip",
        value: "127.0.0.1",
        ...
    }

    Result Example:
    {
        "outcome": "success | failure", # was this execution a success or failure?
        "format": "link", # What format is the output in?
        "output": "http://example.com" # The output of the action. Can be any data structure.
    }
    """
    # fetcher/<plugin_id>/<fetcher_id>/status/<task_id>
    @mcp.prompt("get_fetcher_status")
    def get_fetcher_status_prompt()->str:
        return """Get the status or result of a fetcher

    Variables:
    plugin_id (str): the ID of the plugin who owns the action to execute
    fetcher_id (str): the ID of the action to execute
    task_id (str): the ID of the specific task to get the status of

    Arguments:
    None

    Result Example:
    {
        "outcome": "success | failure", # was this execution a success or failure?
        "format": "link", # What format is the output in?
        "output": "http://example.com" # The output of the action. Can be any data structure.
    }
    """

    # ---- lookup.py -----
    # lookup/types/
    @mcp.prompt("get_types")
    def get_types_prompt() -> str: 
        return """Return the supported types of each external service.

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of sources with their supported types.
        <source_name>: [
            <type name>,
            <type name>,
            ...,
        ],
        ...,
    }
    """
    # lookup/types_detection/
    @mcp.prompt("get_types_detection")
    def get_types_detection_prompt()->str:
        return """Return the regular expression to detect the different types

    Variables:
    None

    Arguments:
    None

    Result Example:
    { # A dictionary of types with their associated regular expressions
        <type>: <regex>,
        ...
    }
    """

    # lookup/enrich
    @mcp.prompt(name="bulk_enrich")
    def bulk_enrich_prompt()->str:
        return """Search other services for additional information related to the provided data.

    Variables:
    None

    Optional Arguments:
    classification: string  => Classification of the type [Default: minimum configured classification]
    sources: string         => | separated list of data sources.
        A source prefixed with '-' will be excluded. Exclusion takes precedence over inclusion.
        If sources is empty or only exclusions, all default configured sources are used (with exclusions applied).
        Note, a source list that includes and excludes the same sources (e.g. sources=vt|-vt) is not treated as empty.
    max_timeout: number     => Maximum execution time for the call in seconds
    limit: number           => limit the amount of returned results counted per source
    no_annotation: boolean  => Do not return any anotations
    no_cache: boolean       => Skip the cache and ask the plugins again
    include_raw: boolean    => Return raw plugin data
    exclude_unset: boolean  => Do not return any values that were not set by the plugin

    Data Block:
    [
        {"type": "ip", "value": "127.0.0.1"},
        ...
    ]

    Result Example:
    {                           # Dictionary of data source queried
        "ip": {
            "127.0.0.1":{
                "vt": {
                    "error": null,          # Error message returned by data source
                    "items": [              # list of results from the source
                        {
                            "link": "https://www.virustotal.com/gui/url/<id>",  # link to results
                            "count": 1,                                         # number of hits from the search
                            "classification": "TLP:C",                          # classification of the search result
                            "annotations": [                                    # Semi structured details about data
                                <Annotation data>
                            ],
                        },
                        ...,
                    ],
                },
                ...,
            },
            ...
        },
        ...
    }
    """

    # lookup/enrich/<type_name>/<value>/
    @mcp.prompt(name="enrich")
    def enrich()->str:
        return """Search other services for additional information related to the provided data.

    Variables:
    type_name => Type of data to lookup in the external system.
    value => Value of the data to lookup. *Must be double URL encoded.*

    Optional Arguments:
    classification: string  => Classification of the type [Default: minimum configured classification]
    sources: string         => | separated list of data sources.
        A source prefixed with '-' will be excluded. Exclusion takes precedence over inclusion.
        If sources is empty or only exclusions, all default configured sources are used (with exclusions applied).
        Note, a source list that includes and excludes the same sources (e.g. sources=vt|-vt) is not treated as empty.
    max_timeout: number     => Maximum execution time for the call in seconds
    limit: number           => limit the amount of returned results counted per source
    no_annotation: boolean  => Do not return any anotations
    no_cache: boolean       => Skip the cache and ask the plugins again
    include_raw: boolean    => Return raw plugin data
    exclude_unset: boolean  => Do not return any values that were not set by the plugin

    API Call Examples:
    /api/v1/lookup/enrich/domain/malicious.domain/
    /api/v1/lookup/enrich/ip/1.1.1.1/?sources=vt|malware_bazar

    Result Example:
    {                           # Dictionary of data source queried
        "vt": {
            "error": null,          # Error message returned by data source
            "items": [              # list of results from the source
                {
                    "link": "https://www.virustotal.com/gui/url/<id>",   # link to results
                    "count": 1,                                          # number of hits from the search
                    "classification": "TLP:C",                           # classification of the search result
                    "annotations": [                                      # Semi structured details about type of data
                        <Annotation data>
                    ],
                },
                ...,
            ],
        },
        ...,
    }
    """

    # ---- static.py ----

    # static/docs
    @mcp.prompt(name="serve_documentation")
    def serve_documentation()->str:
        return """Returns all documentation or filtered documentation if given a url param of a file name or a path

    Variables:
    None

    Arguments:
    None

    Result Example:
    URL Link: /api/v1/static/docs?filter="howler"

    {"howler-docs.md": "Markdown documentation of howler-docs.md"}

    """

    # static/docs/<path:filename>
    @mcp.prompt(name="serve_documentation_file")
    def serve_documentation_file_prompt()->str:
        return """Returns the specific file asked for within the route param

    Variables:
    filename (str): the specific file requested with an extension (i.e. *.md)

    Arguments:
    None

    Result Example:
    URL Link: /api/v1/static/docs/howler-docs.md

    {"markdown": "Markdown documentation of howler-docs.md"}

    """
