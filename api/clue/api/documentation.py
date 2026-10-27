from textwrap import dedent

from flask import current_app, request

from clue.api import ok
from clue.security import api_login


#####################################
# API DOCUMENTATION
# noinspection PyProtectedMember,PyBroadException
@api_login(audit=False)
def get_api_documentation(**_):
    """Full API doc. Loop through all registered API paths and display their documentation.

    Returns a list of API definition.

    Variables:
    None

    Arguments:
    None

    Result Example:
    [
     {'name': "Api Doc",                # Name of the api
      'path': "/api/path/<variable>/",  # API path
      'methods': ["GET", "POST"],       # Allowed HTTP methods
      'description': "API doc.",        # API documentation
      'id': "api_doc",                  # Unique ID for the API
      'function': "apiv1.api_doc",      # Function called in the code
      'protected': False,               # Does the API require login?
      'complete' : True},               # Is the API stable?
      ...]
    """
    api_prefix = f"{request.path.rstrip('/')}/"
    api_version = api_prefix.strip("/").split("/")[-1]
    api_blueprints = {}
    api_list = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith(api_prefix):
            methods = [item for item in (rule.methods or []) if item != "OPTIONS" and item != "HEAD"]

            func = current_app.view_functions[rule.endpoint]
            doc_string = func.__doc__
            func_title = " ".join([x.capitalize() for x in rule.endpoint[rule.endpoint.rindex(".") + 1 :].split("_")])
            blueprint = rule.endpoint[: rule.endpoint.rindex(".")]
            if blueprint == request.blueprint:
                blueprint = "documentation"

            if blueprint not in api_blueprints:
                try:
                    doc = current_app.blueprints[rule.endpoint[: rule.endpoint.rindex(".")]]._doc  # type: ignore[attr-defined]
                except Exception:
                    doc = ""

                api_blueprints[blueprint] = doc

            if doc_string:
                description = dedent(doc_string)
            else:
                description = "[INCOMPLETE]\n\nTHIS API HAS NOT BEEN DOCUMENTED YET!"

            api_id = rule.endpoint.replace(f"{request.blueprint}.", "").replace(".", "_")

            api_list.append(
                {
                    "protected": func.__dict__.get("protected", False),
                    "name": func_title,
                    "id": api_id,
                    "function": f"api.{api_version}.{rule.endpoint}",
                    "path": rule.rule,
                    "methods": methods,
                    "description": description,
                    "complete": "[INCOMPLETE]" not in description,
                }
            )

    return ok({"apis": api_list, "blueprints": api_blueprints})
