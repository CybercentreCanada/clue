import json
import logging
from typing import Any

from clue.common.logging import sanitize_log_value
from clue.common.logging.format import APP_NAME

# Extra fields attached to every audit log record
AUDIT_FIELDS = ("user", "classification", "function", "method", "path")


class AuditSanitizeFilter(logging.Filter):
    """Strips control characters from the message and audit fields of every record emitted by the audit logger."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D102
        record.msg = sanitize_log_value(record.getMessage())
        record.args = None

        for field in AUDIT_FIELDS:
            setattr(record, field, sanitize_log_value(getattr(record, field, "N/A")))

        return True


class AuditJsonFormatter(logging.Formatter):
    """Formats audit records as a single line of JSON, escaping every value with json.dumps."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
        data: dict[str, Any] = {
            "date": self.formatTime(record, self.datefmt),
            "type": "audit",
            "app_name": APP_NAME,
            "api": f"{APP_NAME}.api.audit",
            "severity": record.levelname,
        }
        data.update({field: getattr(record, field, "N/A") for field in AUDIT_FIELDS})

        if message := record.getMessage():
            data["message"] = message

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data)
