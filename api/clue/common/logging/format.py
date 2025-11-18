import json

from clue.common.str_utils import default_string_value

hostname = "unknownhost"
# noinspection PyBroadException
try:
    import socket

    hostname = socket.gethostname()
except Exception:  # noqa: S110
    pass

APP_NAME: str = default_string_value(env_name="APP_NAME", default="clue")  # type: ignore[assignment]

CLUE_SYSLOG_FORMAT = f"HWL %(levelname)8s {hostname} %(process)5d %(name)40s | %(message)s"
CLUE_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s | %(message)s"
CLUE_DATE_FORMAT = "%y/%m/%d %H:%M:%S"
CLUE_JSON_FORMAT = (
    f"{{"
    f'"@timestamp": "%(asctime)s", '
    f'"event": {{ "module": "{APP_NAME}", "dataset": "%(name)s" }}, '
    f'"host": {{ "hostname": "{hostname}" }}, '
    f'"log": {{ "level": "%(levelname)s", "logger": "%(name)s" }}, '
    f'"process": {{ "pid": "%(process)d" }}, '
    f'"message": %(message)s}}'
)
CLUE_ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
CLUE_AUDIT_FORMAT = json.dumps(
    {
        "date": "%(asctime)s",
        "type": "audit",
        "app_name": APP_NAME,
        "api": f"{APP_NAME}.api.audit",
        "severity": "%(levelname)s",
        "user": "%(user)s",
        "classification": "%(classification)s",
        "function": "%(function)s",
        "method": "%(method)s",
        "path": "%(path)s",
    }
).replace('"msg"', "%(message)s")
