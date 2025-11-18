import logging
import os
import sys

from flask import request

from clue.common.logging.format import (
    CLUE_AUDIT_FORMAT,
    CLUE_DATE_FORMAT,
    CLUE_ISO_DATE_FORMAT,
    CLUE_LOG_FORMAT,
)
from clue.config import DEBUG, config

AUDIT = config.api.audit

AUDIT_KW_TARGET = [
    "sid",
    "sha256",
    "copy_sid",
    "filter",
    "query",
    "username",
    "group",
    "rev",
    "wq_id",
    "index",
    "cache_key",
    "alert_key",
    "alert_id",
    "url",
    "q",
    "fq",
    "file_hash",
    "heuristic_id",
    "error_key",
    "mac",
    "vm_type",
    "vm_name",
    "config_name",
    "servicename",
    "vm",
    "transition",
    "data",
    "id",
    "comment_id",
    "label_set",
    "tool_name",
    "operation_id",
    "category",
    "label",
    "type_name",
    "type",
    "value",
]

AUDIT_LOG = logging.getLogger("clue.api.audit")
AUDIT_LOG.propagate = False

if AUDIT:
    AUDIT_LOG.setLevel(logging.DEBUG)

if not os.path.exists(config.logging.log_directory):
    os.makedirs(config.logging.log_directory)

fh = logging.FileHandler(os.path.join(config.logging.log_directory, "clue_audit.log"))
fh.setLevel(logging.DEBUG)
fh.setFormatter(
    logging.Formatter(
        CLUE_LOG_FORMAT if DEBUG else CLUE_AUDIT_FORMAT,
        CLUE_DATE_FORMAT if DEBUG else CLUE_ISO_DATE_FORMAT,
    )
)
AUDIT_LOG.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(
    logging.Formatter(
        CLUE_LOG_FORMAT if DEBUG else CLUE_AUDIT_FORMAT,
        CLUE_DATE_FORMAT if DEBUG else CLUE_ISO_DATE_FORMAT,
    )
)
AUDIT_LOG.addHandler(ch)

#########################
# End of prepare logger #
#########################


def audit(args, kwargs, user, func, impersonator=None):
    """Audit

    Arguments:

    """
    try:
        json_blob = request.json
        if not isinstance(json_blob, dict):
            json_blob = {}
    except Exception:
        json_blob = {}

    try:
        req_args = ["%s='%s'" % (k, v) for k, v in request.args.items() if k in AUDIT_KW_TARGET]
        method = request.method
        path = request.path
    except RuntimeError:
        req_args = []
        method = "N/A"
        path = "N/A"

    params_list = (
        list(args)
        + ["%s='%s'" % (k, v) for k, v in kwargs.items() if k in AUDIT_KW_TARGET]
        + req_args
        + ["%s='%s'" % (k, v) for k, v in json_blob.items() if k in AUDIT_KW_TARGET]
    )

    if impersonator:
        audit_user = f"{impersonator} on behalf of {user['uname']}"
    else:
        audit_user = user["uname"]

    if DEBUG:
        # In debug mode, you'll get an output like:
        # 23/03/20 14:26:56 DEBUG clue.api.audit | goose - search(index='...', query='...')
        AUDIT_LOG.debug(
            "%s [%s]- %s(%s)",
            audit_user,
            user["classification"],
            func.__name__,
            ", ".join(params_list),
        )
    else:
        # In prod, you'll get an output like:
        # {
        #     "date": "2023-03-20T18:33:27-0400",
        #     "type": "audit",
        #     "app_name": "clue",
        #     "api": "clue.api.audit",
        #     "severity": "INFO",
        #     "user": "goose",
        #     "function": "search(index='hit', query='blah blah')",
        #     "method": "POST",
        #     "path": "/api/v1/search/hit/"
        # }
        AUDIT_LOG.info(
            "",
            extra={
                "user": audit_user,
                "function": f"{func.__name__}({', '.join(params_list)})",
                "method": method,
                "path": path,
                "classification": user["classification"],
            },
        )
