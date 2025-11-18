import clue.services.config_service as config_service
from clue.api import make_subapi_blueprint, not_found, ok
from clue.common.swagger import generate_swagger_docs
from clue.models.network import QueryResult

SUB_API = "configs"
configs_api = make_subapi_blueprint(SUB_API, api_version=1)
configs_api._doc = "Read configuration data about the system"


@generate_swagger_docs()
@configs_api.route("/", methods=["GET"])
def configs(**kwargs):
    """Return all of the configuration information about the deployment.

    Variables:
    None

    Arguments:
    None

    Result Example:
    {
        "configuration": {                         # Configuration block
            "auth": {                                # Authentication block
                "oauth_providers": [                   # List of oAuth providers available
                    "azure_ad",
                    "keyclock",
                    ...
                ],
            },
            "system": {                              # System Configuration
                "branch": "develop",                   # Branch the current deployment is connected to
                "commit": "123456789abcdef",           # Last commit ID
                "version": "1.0"                       # Clue version
            },
            "ui": {                                  # UI Configuration
                "apps": [],                            # List of apps shown in the apps switcher
            }
        },
        "c12nDef": {},                             # Classification definition block
    }

    """
    return ok(config_service.get_configuration())


@configs_api.route("/schema/<model>", methods=["GET"])
def schemas(model: str, **kwargs):
    """Return a JSON schema for a given model.

    Variables:
    model   =>  The model for which to return the schema. Valid options: plugin_response

    Arguments:
    None

    Result Example:
    {
        "properties": {
            "error": {
                "anyOf": [
                    {
                        "type": "string"
                    },
                    {
                        "type": "null"
                    }
                ],
                "default": null,
                "description": "Error message returned by data source",
                "title": "Error"
            },
            ...
        },
        "title": "QueryResult",
        "type": "object"
    }
    """
    if model == "plugin_response":
        return ok(QueryResult.model_json_schema())

    return not_found(err="Not a valid model")
