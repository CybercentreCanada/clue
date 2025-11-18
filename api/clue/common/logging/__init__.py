import json
import logging
import logging.handlers
import os
import re
import uuid
from traceback import format_exception
from typing import Optional, Self, Union

from flask import request

from clue.common.logging.format import (
    CLUE_DATE_FORMAT,
    CLUE_JSON_FORMAT,
    CLUE_LOG_FORMAT,
    CLUE_SYSLOG_FORMAT,
)
from clue.common.str_utils import default_string_value

LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "DISABLED": 60,
}

DEBUG = False


class JsonFormatter(logging.Formatter):
    """A custom implementation of logging.Formatter that supports json logs as well as traceback for exceptions.

    Args:
        logging (str): The template to use for the logs
    """

    def formatMessage(self: Self, record: logging.LogRecord):  # noqa: N802
        """Formats record.message as json, and formats exceptions using traceback.

        Args:
            record (logging.LogRecord): The log record to format

        Returns:
            str: The formatted log
        """
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)
            record.exc_info = None

        if record.exc_text:
            record.msg += "\n" + record.exc_text
            record.exc_text = None

        record.msg = json.dumps(record.msg)

        record.asctime = self.formatTime(record, self.datefmt)

        record.message = record.msg

        return self._style.format(record)

    def formatException(self, exc_info):  # noqa: N802
        """Formats the exception using traceback

        Args:
            exc_info (logging._SysExcInfoType): The exc_info object from the LogRecord

        Returns:
            str: The formatted traceback error
        """
        return "".join(format_exception(*exc_info))


def init_logging(name: str, log_level: Optional[int] = None):  # noqa: C901
    """Initializes the logging stack for an app

    Args:
        name (str): The name of the app
        log_level (Optional[int], optional): The log level to use. Defaults to None.

    Returns:
        Logger: The initialized logger
    """
    from clue.config import config

    app_name: str = default_string_value(env_name="APP_NAME", default="clue")  # type: ignore[assignment]

    logger = logging.getLogger(app_name)

    # Test if we've initialized the log handler already.
    if len(logger.handlers) != 0:
        return logger.getChild(name)

    if name.startswith(f"{app_name}."):
        name = name[len(app_name) + 1 :]

    debug = config.api.debug
    config.logging.log_to_console = config.logging.log_to_console or debug

    if log_level is None:
        log_level = LOG_LEVEL_MAP[config.logging.log_level]

    logging.root.setLevel(logging.CRITICAL)
    logger.setLevel(log_level)

    if config.logging.log_level == "DISABLED":
        # While log_level is set to disable, we will not create any handlers
        return logger.getChild(name)

    if config.logging.log_to_file:
        if not os.path.isdir(config.logging.log_directory):
            logger.warning(
                "Log directory does not exist. Will try to create %s",
                config.logging.log_directory,
            )
            os.makedirs(config.logging.log_directory)

        if log_level <= logging.DEBUG:
            dbg_file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(config.logging.log_directory, f"{name}.dbg"),
                maxBytes=10485760,
                backupCount=5,
            )
            dbg_file_handler.setLevel(logging.DEBUG)
            if config.logging.log_as_json:
                dbg_file_handler.setFormatter(JsonFormatter(CLUE_JSON_FORMAT))
            else:
                dbg_file_handler.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
            logger.addHandler(dbg_file_handler)

        if log_level <= logging.INFO:
            op_file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(config.logging.log_directory, f"{name}.log"),
                maxBytes=10485760,
                backupCount=5,
            )
            op_file_handler.setLevel(logging.INFO)
            if config.logging.log_as_json:
                op_file_handler.setFormatter(JsonFormatter(CLUE_JSON_FORMAT))
            else:
                op_file_handler.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
            logger.addHandler(op_file_handler)

        if log_level <= logging.ERROR:
            err_file_handler = logging.handlers.RotatingFileHandler(
                os.path.join(config.logging.log_directory, f"{name}.err"),
                maxBytes=10485760,
                backupCount=5,
            )
            err_file_handler.setLevel(logging.ERROR)
            if config.logging.log_as_json:
                err_file_handler.setFormatter(JsonFormatter(CLUE_JSON_FORMAT))
            else:
                err_file_handler.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
            logger.addHandler(err_file_handler)

    if config.logging.log_to_console:
        console = logging.StreamHandler()
        if config.logging.log_as_json:
            console.setFormatter(JsonFormatter(CLUE_JSON_FORMAT))
        else:
            console.setFormatter(logging.Formatter(CLUE_LOG_FORMAT, CLUE_DATE_FORMAT))
        logger.addHandler(console)

    if config.logging.log_to_syslog and config.logging.syslog_host and config.logging.syslog_port:
        syslog_handler = logging.handlers.SysLogHandler(
            address=(config.logging.syslog_host, config.logging.syslog_port)
        )
        syslog_handler.formatter = logging.Formatter(CLUE_SYSLOG_FORMAT)
        logger.addHandler(syslog_handler)

    return logger.getChild(name)


def get_logger(name: Optional[str] = None, parent: Optional[logging.Logger] = None) -> logging.Logger:
    """Gets the logger for a specified python file

    Args:
        name (Optional[str], optional): The name of the python file. Defaults to None.
        parent (Optional[logging.Logger], optional): The parent of the file. Defaults to None.

    Returns:
        logging.Logger: _description_
    """
    if name:
        name = (
            re.sub(r".+clue(-api)?/", "", re.sub(r".+plugins/", "", name))
            .replace("/", ".")
            .replace(".__init__", "")
            .replace(".py", "")
        )
        name = re.sub(r"^api\.?", "", name)

    logger = parent or init_logging("api")

    if name:
        logger = logger.getChild(name)

    return logger


def get_traceback_info(tb):
    """Gets the traceback info of a traceback"""
    tb_list = []
    tb_id = 0
    last_ui = None
    while tb is not None:
        f = tb.tb_frame
        line_no = tb.tb_lineno
        tb_list.append((f, line_no))
        tb = tb.tb_next
        if "/ui/" in f.f_code.co_filename:
            last_ui = tb_id
        tb_id += 1

    if last_ui is not None:
        tb_frame, line = tb_list[last_ui]
        user = tb_frame.f_locals.get("kwargs", {}).get("user", None)

        if not user:
            temp = tb_frame.f_locals.get("_", {})
            if isinstance(temp, dict):
                user = temp.get("user", None)

        if not user:
            user = tb_frame.f_locals.get("user", None)

        if not user:
            user = tb_frame.f_locals.get("impersonator", None)

        if user:
            return user, tb_frame.f_code.co_filename, tb_frame.f_code.co_name, line

        return None

    return None


def dumb_log(log, msg, is_exception=False):
    """Logs a message to a generic logger."""
    args: Union[str, bytes] = request.query_string
    if isinstance(args, bytes):
        args = args.decode()

    if args:
        args = f"?{args}"

    message = f"{msg} - {request.path}{args}"
    if is_exception:
        log.exception(message)
    else:
        log.warning(message)


def log_with_traceback(traceback, msg, is_exception=False, audit=False):
    """Logs a message with a traceback"""
    log = get_logger("traceback") if not audit else logging.getLogger("clue.api.audit")

    tb_info = get_traceback_info(traceback)
    if tb_info:
        tb_user, tb_file, tb_function, tb_line_no = tb_info
        args: Optional[Union[str, bytes]] = request.query_string
        if args:
            args = f"?{args if isinstance(args, str) else args.decode()}"
        else:
            args = ""

        # noinspection PyBroadException
        try:
            message = (
                f'{tb_user["uname"]} [{tb_user["classification"]}] :: {msg} - {tb_file}:{tb_function}:{tb_line_no}'
                f'[{os.environ.get("CLUE_VERSION", "0.0.0.dev0")}] ({request.path}{args})'
            )
            if is_exception:
                log.exception(message)
            else:
                log.warning(message)
        except Exception:
            dumb_log(log, msg, is_exception=is_exception)
    else:
        dumb_log(log, msg, is_exception=is_exception)


def log_error(logger, msg, err=None, status_code=None):
    """Log a standard error string, with a unique id reference for logging."""
    err_id = str(uuid.uuid4())
    error = [msg]
    if status_code:
        error.append(f"{status_code=}")
    if err:
        error.append(f"{err=}")
    error.append(f"{err_id}")
    logger.error(" :: ".join(error))
    return err_id
