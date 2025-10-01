import logging
import tempfile
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from clue.common.logging import (
    LOG_LEVEL_MAP,
    JsonFormatter,
    dumb_log,
    get_logger,
    get_traceback_info,
    init_logging,
    log_error,
    log_with_traceback,
)
from clue.common.logging.format import CLUE_JSON_FORMAT


@pytest.fixture
def flask_app():
    """Create a Flask app for request context testing."""
    app = Flask(__name__)
    with app.app_context():
        yield app


@pytest.fixture
def temp_log_dir():
    """Create a temporary log directory for testing file logging."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="module", autouse=True)
def reset_logger():
    yield True

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()

    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True


class TestJsonFormatter:
    """Test cases for JsonFormatter class."""

    def test_format_message_simple(self):
        """Test that JsonFormatter correctly formats simple messages as JSON."""
        formatter = JsonFormatter(CLUE_JSON_FORMAT)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.formatMessage(record)
        assert '"Test message"' in result

    def test_format_message_with_exception(self):
        """Test that JsonFormatter correctly handles exceptions with traceback."""
        formatter = JsonFormatter(CLUE_JSON_FORMAT)
        try:
            raise ValueError("Test exception")  # noqa: TRY301
        except ValueError:
            exc_info = logging.sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.formatMessage(record)
        assert "Test error" in result
        assert "ValueError" in result

    def test_format_exception(self):
        """Test that formatException returns formatted traceback."""
        formatter = JsonFormatter(CLUE_JSON_FORMAT)
        try:
            raise ValueError("Test exception")  # noqa: TRY301
        except ValueError:
            exc_info = logging.sys.exc_info()

        result = formatter.formatException(exc_info)
        assert "ValueError: Test exception" in result
        assert "Traceback" in result


class TestLogLevelMap:
    """Test cases for LOG_LEVEL_MAP constant."""

    def test_log_level_map_completeness(self):
        """Test that LOG_LEVEL_MAP contains all expected log levels."""
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "DISABLED"]
        assert all(level in LOG_LEVEL_MAP for level in expected_levels)

    def test_log_level_map_values(self):
        """Test that LOG_LEVEL_MAP maps to correct logging constants."""
        assert LOG_LEVEL_MAP["DEBUG"] == logging.DEBUG
        assert LOG_LEVEL_MAP["INFO"] == logging.INFO
        assert LOG_LEVEL_MAP["WARNING"] == logging.WARNING
        assert LOG_LEVEL_MAP["ERROR"] == logging.ERROR
        assert LOG_LEVEL_MAP["CRITICAL"] == logging.CRITICAL
        assert LOG_LEVEL_MAP["DISABLED"] == 60


class TestInitLogging:
    """Test cases for init_logging function."""

    @patch("clue.common.logging.default_string_value")
    @patch("clue.config.config")
    def test_init_logging_basic(self, mock_config_obj, mock_default_string):
        """Test basic logger initialization."""
        mock_default_string.return_value = "clue"

        mock_config_obj.api.debug = False
        mock_config_obj.logging.log_level = "INFO"
        mock_config_obj.logging.log_to_console = True
        mock_config_obj.logging.log_to_file = False
        mock_config_obj.logging.log_directory = "/tmp/test_logs"
        mock_config_obj.logging.log_as_json = False
        mock_config_obj.logging.log_to_syslog = False
        mock_config_obj.logging.syslog_host = "localhost"
        mock_config_obj.logging.syslog_port = 514

        # Clear existing handlers to ensure clean test
        logger = logging.getLogger("clue")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        result = init_logging("test")
        assert result.name == "clue.test"

    @patch("clue.common.logging.default_string_value")
    @patch("clue.config.config")
    def test_init_logging_already_initialized(self, mock_config_obj, mock_default_string):
        """Test that init_logging returns existing logger if already initialized."""
        mock_default_string.return_value = "clue"

        mock_config_obj.api.debug = False
        mock_config_obj.logging.log_level = "INFO"
        mock_config_obj.logging.log_to_console = True
        mock_config_obj.logging.log_to_file = False
        mock_config_obj.logging.log_directory = "/tmp/test_logs"
        mock_config_obj.logging.log_as_json = False
        mock_config_obj.logging.log_to_syslog = False
        mock_config_obj.logging.syslog_host = "localhost"
        mock_config_obj.logging.syslog_port = 514

        # Pre-initialize logger with handlers
        logger = logging.getLogger("clue")
        logger.addHandler(logging.StreamHandler())

        result = init_logging("test")
        assert result.name == "clue.test"

    @patch("clue.common.logging.default_string_value")
    @patch("clue.config.config")
    def test_init_logging_disabled(self, mock_config_obj, mock_default_string):
        """Test that init_logging handles disabled logging correctly."""
        mock_default_string.return_value = "clue"

        mock_config_obj.api.debug = False
        mock_config_obj.logging.log_level = "DISABLED"
        mock_config_obj.logging.log_to_console = False
        mock_config_obj.logging.log_to_file = False
        mock_config_obj.logging.log_directory = "/tmp/test_logs"
        mock_config_obj.logging.log_as_json = False
        mock_config_obj.logging.log_to_syslog = False
        mock_config_obj.logging.syslog_host = "localhost"
        mock_config_obj.logging.syslog_port = 514

        # Clear existing handlers
        logger = logging.getLogger("clue")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        result = init_logging("test")
        assert result.name == "clue.test"
        assert len(logger.handlers) == 0

    @patch("clue.common.logging.default_string_value")
    @patch("clue.config.config")
    @patch("os.path.isdir")
    @patch("os.makedirs")
    def test_init_logging_file_logging(
        self, mock_makedirs, mock_isdir, mock_config_obj, mock_default_string, temp_log_dir
    ):
        """Test file logging initialization."""
        mock_default_string.return_value = "clue"

        mock_config_obj.api.debug = False
        mock_config_obj.logging.log_to_console = False
        mock_config_obj.logging.log_as_json = False
        mock_config_obj.logging.log_to_syslog = False
        mock_config_obj.logging.syslog_host = "localhost"
        mock_config_obj.logging.syslog_port = 514
        mock_config_obj.logging.log_to_file = True
        mock_config_obj.logging.log_directory = temp_log_dir
        mock_config_obj.logging.log_level = "DEBUG"
        mock_isdir.return_value = True

        # Clear existing handlers
        logger = logging.getLogger("clue")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        result = init_logging("test", logging.DEBUG)
        assert result.name == "clue.test"

    @patch("clue.common.logging.default_string_value")
    @patch("clue.config.config")
    def test_init_logging_syslog(self, mock_config_obj, mock_default_string, temp_log_dir):
        """Test syslog handler initialization."""
        mock_default_string.return_value = "clue"

        mock_config_obj.api.debug = False
        mock_config_obj.logging.log_to_console = False
        mock_config_obj.logging.log_as_json = False
        mock_config_obj.logging.log_to_file = True
        mock_config_obj.logging.log_directory = temp_log_dir
        mock_config_obj.logging.log_level = "DEBUG"
        mock_config_obj.logging.log_to_syslog = True
        mock_config_obj.logging.syslog_host = "localhost"
        mock_config_obj.logging.syslog_port = 514

        # Clear existing handlers
        logger = logging.getLogger("clue")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        with patch("logging.handlers.SysLogHandler") as mock_syslog:
            mock_syslog_handler = Mock()
            mock_syslog.return_value = mock_syslog_handler

            result = init_logging("test")
            assert result.name == "clue.test"
            mock_syslog.assert_called_once_with(address=("localhost", 514))


class TestGetLogger:
    """Test cases for get_logger function."""

    @patch("clue.common.logging.init_logging")
    def test_get_logger_no_name(self, mock_init_logging):
        """Test get_logger with no name parameter."""
        mock_logger = Mock()
        mock_init_logging.return_value = mock_logger

        result = get_logger()
        mock_init_logging.assert_called_once_with("api")
        assert result == mock_logger

    @patch("clue.common.logging.init_logging")
    def test_get_logger_with_name(self, mock_init_logging):
        """Test get_logger with name parameter."""
        mock_parent_logger = Mock()
        mock_child_logger = Mock()
        mock_parent_logger.getChild.return_value = mock_child_logger
        mock_init_logging.return_value = mock_parent_logger

        result = get_logger("test.module")
        assert result == mock_child_logger
        mock_parent_logger.getChild.assert_called_once()

    @patch("clue.common.logging.init_logging")
    def test_get_logger_path_normalization(self, mock_init_logging):
        """Test that get_logger normalizes file paths correctly."""
        mock_parent_logger = Mock()
        mock_child_logger = Mock()
        mock_parent_logger.getChild.return_value = mock_child_logger
        mock_init_logging.return_value = mock_parent_logger

        # Test various path formats
        test_paths = [
            "/path/to/clue/module.py",
            "/path/to/clue-api/module.py",
            "/path/to/plugins/module.py",
            "api.module.py",
            "module/__init__.py",
        ]

        for path in test_paths:
            get_logger(path)

        # Should have been called for each path
        assert mock_parent_logger.getChild.call_count == len(test_paths)

    def test_get_logger_with_parent(self):
        """Test get_logger with explicit parent logger."""
        parent_logger = Mock()
        child_logger = Mock()
        parent_logger.getChild.return_value = child_logger

        result = get_logger("test", parent=parent_logger)
        assert result == child_logger
        parent_logger.getChild.assert_called_once_with("test")


class TestGetTracebackInfo:
    """Test cases for get_traceback_info function."""

    def test_get_traceback_info_no_ui(self):
        """Test get_traceback_info with traceback not containing UI path."""
        try:
            raise ValueError("Test exception")  # noqa: TRY301
        except ValueError:
            # We don't need the actual traceback for this mock test
            pass

        # Create a mock traceback without UI path
        mock_tb = Mock()
        mock_tb.tb_frame.f_code.co_filename = "/some/path/file.py"
        mock_tb.tb_frame.f_locals = {}
        mock_tb.tb_lineno = 42
        mock_tb.tb_next = None

        result = get_traceback_info(mock_tb)
        assert result is None

    def test_get_traceback_info_with_ui_no_user(self):
        """Test get_traceback_info with UI path but no user info."""
        mock_tb = Mock()
        mock_tb.tb_frame.f_code.co_filename = "/some/path/ui/file.py"
        mock_tb.tb_frame.f_code.co_name = "test_function"
        mock_tb.tb_frame.f_locals = {}
        mock_tb.tb_lineno = 42
        mock_tb.tb_next = None

        result = get_traceback_info(mock_tb)
        assert result is None

    def test_get_traceback_info_with_ui_and_user(self):
        """Test get_traceback_info with UI path and user info."""
        mock_tb = Mock()
        mock_tb.tb_frame.f_code.co_filename = "/some/path/ui/file.py"
        mock_tb.tb_frame.f_code.co_name = "test_function"
        mock_tb.tb_frame.f_locals = {"kwargs": {"user": {"uname": "testuser", "classification": "TLP:CLEAR"}}}
        mock_tb.tb_lineno = 42
        mock_tb.tb_next = None

        result = get_traceback_info(mock_tb)
        assert result is not None
        assert result[0]["uname"] == "testuser"
        assert result[1] == "/some/path/ui/file.py"
        assert result[2] == "test_function"
        assert result[3] == 42


class TestDumbLog:
    """Test cases for dumb_log function."""

    def test_dumb_log_warning(self, flask_app):
        """Test dumb_log with warning level."""
        mock_logger = Mock()

        with flask_app.test_request_context("/test?param=value"):
            dumb_log(mock_logger, "Test message", is_exception=False)

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0]
        assert "Test message - /test?param=value" in call_args[0]

    def test_dumb_log_exception(self, flask_app):
        """Test dumb_log with exception level."""
        mock_logger = Mock()

        with flask_app.test_request_context("/test"):
            dumb_log(mock_logger, "Test error", is_exception=True)

        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args[0]
        assert "Test error - /test" in call_args[0]

    def test_dumb_log_bytes_query_string(self, flask_app):
        """Test dumb_log handles bytes query string correctly."""
        mock_logger = Mock()

        with flask_app.test_request_context("/test?param=value"):
            # Mock request.query_string as bytes
            with patch("clue.common.logging.request") as mock_request:
                mock_request.query_string = b"param=value"
                mock_request.path = "/test"
                dumb_log(mock_logger, "Test message")

        mock_logger.warning.assert_called_once()


class TestLogWithTraceback:
    """Test cases for log_with_traceback function."""

    @patch("clue.common.logging.get_logger")
    @patch("clue.common.logging.get_traceback_info")
    def test_log_with_traceback_no_info(self, mock_get_tb_info, mock_get_logger, flask_app):
        """Test log_with_traceback when no traceback info is available."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_get_tb_info.return_value = None

        mock_tb = Mock()

        with flask_app.test_request_context("/test"):
            log_with_traceback(mock_tb, "Test message")

        mock_logger.warning.assert_called_once()

    @patch("clue.common.logging.get_logger")
    @patch("clue.common.logging.get_traceback_info")
    @patch.dict("os.environ", {"CLUE_VERSION": "1.0.0"})
    def test_log_with_traceback_with_info(self, mock_get_tb_info, mock_get_logger, flask_app):
        """Test log_with_traceback with valid traceback info."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_get_tb_info.return_value = (
            {"uname": "testuser", "classification": "TLP:CLEAR"},
            "/path/to/file.py",
            "test_function",
            42,
        )

        mock_tb = Mock()

        with flask_app.test_request_context("/test"):
            log_with_traceback(mock_tb, "Test message")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0]
        assert "testuser" in call_args[0]
        assert "TLP:CLEAR" in call_args[0]

    @patch("clue.common.logging.get_logger")
    @patch("clue.common.logging.get_traceback_info")
    def test_log_with_traceback_audit_mode(self, mock_get_tb_info, mock_get_logger, flask_app):
        """Test log_with_traceback in audit mode."""
        mock_logger = Mock()
        mock_get_tb_info.return_value = None

        with patch("logging.getLogger") as mock_logging_get_logger:
            mock_logging_get_logger.return_value = mock_logger

            mock_tb = Mock()

            with flask_app.test_request_context("/test"):
                log_with_traceback(mock_tb, "Test message", audit=True)

            mock_logging_get_logger.assert_called_once_with("clue.api.audit")

    @patch("clue.common.logging.get_logger")
    @patch("clue.common.logging.get_traceback_info")
    def test_log_with_traceback_exception_in_formatting(self, mock_get_tb_info, mock_get_logger, flask_app):
        """Test log_with_traceback handles exceptions during message formatting."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Return invalid traceback info that will cause formatting to fail
        mock_get_tb_info.return_value = ("invalid", "data", "format", "here")

        mock_tb = Mock()

        with flask_app.test_request_context("/test"):
            log_with_traceback(mock_tb, "Test message")

        # Should fall back to dumb_log
        mock_logger.warning.assert_called_once()


class TestLogError:
    """Test cases for log_error function."""

    def test_log_error_basic(self):
        """Test basic log_error functionality."""
        mock_logger = Mock()

        result = log_error(mock_logger, "Test error")

        # Should return a UUID
        assert isinstance(result, str)
        assert len(result) == 36  # UUID length

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "Test error" in call_args[0]
        assert result in call_args[0]

    def test_log_error_with_status_code(self):
        """Test log_error with status code."""
        mock_logger = Mock()

        result = log_error(mock_logger, "Test error", status_code=404)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "Test error" in call_args[0]
        assert "status_code=404" in call_args[0]
        assert result in call_args[0]

    def test_log_error_with_exception(self):
        """Test log_error with exception object."""
        mock_logger = Mock()
        test_exception = ValueError("Test exception")

        result = log_error(mock_logger, "Test error", err=test_exception)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "Test error" in call_args[0]
        assert "err=ValueError('Test exception')" in call_args[0]
        assert result in call_args[0]

    def test_log_error_with_all_params(self):
        """Test log_error with all parameters."""
        mock_logger = Mock()
        test_exception = ValueError("Test exception")

        result = log_error(mock_logger, "Test error", err=test_exception, status_code=500)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0]
        assert "Test error" in call_args[0]
        assert "status_code=500" in call_args[0]
        assert "err=ValueError('Test exception')" in call_args[0]
        assert result in call_args[0]

        # Verify it's separated by " :: "
        assert " :: " in call_args[0]
