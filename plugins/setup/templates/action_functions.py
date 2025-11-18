import textwrap

from clue.models.actions import Action, ActionResult, ExecuteRequest
from pydantic_core import Url

# ---

# NOTE: You can instead statically define your actions and pass them directly to the plugin if that's preferred.
# This approach is useful when your actions don't need to change based on user context or runtime conditions.
#
# Example of static action definition:
#
# from clue.plugin import CluePlugin
# from clue.models.actions import Action, ExecuteRequest
#
# ACTIONS = [
#     Action[ExecuteRequest](
#         id="static_test_action",
#         name="Static Test Action",
#         classification="TLP:CLEAR",
#         summary="A statically defined action",
#         supported_types={"ip", "domain"},
#         accept_multiple=False,
#     )
# ]
#
# plugin = CluePlugin(
#     app_name="my-plugin",
#     actions=ACTIONS,  # Pass actions directly to constructor
#     supported_types={"ip", "domain"},
#     classification="TLP:CLEAR",
#     run_action=my_run_action_function,
#     # setup_actions is not needed when using static actions, unless you want to combine the approaches
# )


@plugin.use  # type: ignore  # noqa: F821
def setup_actions(existing_actions: list[Action], token: str | None) -> list[Action]:
    """Setup actions - dynamically define actions available to this plugin.

    This function is called during the plugin lifecycle when the central API requests
    the list of available actions from this plugin (via the /actions endpoint).
    It allows for runtime generation of action definitions, which is useful for:
    - Creating user-specific actions based on authentication token
    - Dynamically configuring actions based on external systems or configurations
    - Modifying action parameters or availability based on runtime conditions

    The function is invoked when:
    1. The central API calls GET /actions on this plugin
    2. The UI refreshes the list of available actions (refreshActions() in ClueActionContext)
    3. During plugin initialization to populate the action registry

    Args:
        existing_actions: Any actions already defined statically in the plugin constructor
        token: Authentication token from the central API (if authentication is enabled)
               Can be used to customize actions based on user permissions or context

    Returns:
        list[Action]: Complete list of actions this plugin supports, including both
                     existing_actions and any dynamically generated ones

    Note:
        This function can be used instead of or in addition to the static 'actions'
        attribute in the CluePlugin constructor for maximum flexibility.
    """
    return [
        Action[ExecuteRequest](
            id="test_action",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Execute a test action",
            supported_types={"$SUPPORTED_TYPES"},
            accept_multiple=False,
        )
    ]


@plugin.use  # type: ignore  # noqa: F821
def run_action(action: Action, request: ExecuteRequest, token: str | None) -> ActionResult:
    """Execute an action when requested by the central API.

    This function is the main entry point for action execution and is called when:
    1. A user triggers an action from the UI (via executeAction() in ClueActionContext)
    2. The central API receives a POST request to /actions/{action_id}
    3. The action form is completed and submitted (if the action requires parameters)

    The execution flow is:
    1. UI calls executeAction() with selector(s) and parameters
    2. ClueActionContext validates parameters against the action's JSON schema
    3. Central API routes the request to this plugin's /actions/{action_id} endpoint
    4. This run_action function is invoked with the validated request
    5. ActionResult is returned and processed by the UI

    UI Integration & User Communication:
    - The ActionResult.summary is displayed as a snackbar notification to the user
    - If ActionResult.link is provided, an "open in new tab" button appears in the snackbar
    - ActionResult.outcome determines the snackbar color (success=green, failure=red)
    - If ActionResult.format is set (and not "pivot"), a modal dialog shows the output
    - If format="pivot", the output URL is opened in a new browser tab
    - ActionResult.output content is rendered based on the format (markdown, json, etc.)

    Args:
        action: The Action definition that was selected for execution
                Contains metadata like id, name, supported_types, etc.
        request: ExecuteRequest containing the selector(s) and any additional parameters
                 If the Action used a custom ExecuteRequest subclass, this will be that type
                 and should be cast accordingly for accessing custom parameters
        token: Authentication token from the central API (if authentication is enabled)
               Can be used for user-specific logic or external API calls

    Returns:
        ActionResult: Result of the action execution that will be communicated to the user
                     - outcome: "success" or "failure" (affects UI notification color)
                     - summary: Brief message shown in snackbar (required)
                     - output: Main result data (optional, displayed in modal if format is set)
                     - format: How to render output ("markdown", "json", "pivot", etc.)
                     - link: Optional URL for additional information (adds button to snackbar)

    Note:
        The function must handle any exceptions internally and return appropriate
        ActionResult with outcome="failure" rather than raising exceptions.
    """
    logger.info("Executing %s with %s", action.id, repr(request))  # type: ignore  # noqa: F821

    summary = textwrap.dedent(
        f"""
        # Selector Data

        Type: {request.selector.type if request.selector else "N/A"}
        Value: {request.selector.value if request.selector else "N/A"}
        Classification: {request.selector.classification if request.selector else "N/A"}
        """
    ).strip()

    return ActionResult(
        outcome="success",
        summary="We got a request",
        format="markdown",
        output=summary,
        link=Url("https://example.com"),
    )
