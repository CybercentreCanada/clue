import re

from clue.common.exceptions import ClueValueError
from clue.config import CLASSIFICATION


def validate_plugin_identifier(value: str) -> str:
    """Allow safe ASCII components separated by dots, never dot segments."""
    if re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", value) is None:
        raise ClueValueError("Invalid plugin identifier.", status_code=400)
    return value


MAX_TASK_ID_LENGTH = 256


def validate_task_id(value: str) -> str:
    """Accept any opaque plugin-issued task id that stays a single path segment once percent-encoded.

    Task ids are minted by plugins (Celery UUIDs by default, but legacy/third-party backends may use other
    formats), so only characters that cannot be safely encoded or routed are rejected. Callers must still encode
    the value with ``quote_plugin_path_segment`` before building an upstream URL.
    """
    if (
        not value
        or len(value) > MAX_TASK_ID_LENGTH
        or value in {".", ".."}
        or "/" in value
        or re.search(r"[\x00-\x1f\x7f]", value)
    ):
        raise ClueValueError("Invalid task id.", status_code=400)
    return value


def validate_classification(classification: str):
    """Validates the provided classification.

    Args:
        classification (str): The classification to validate.

    Raises:
        AssertionError: Raised whenever the provided classification is not valid.

    Returns:
        str: The validated classification.
    """
    if not CLASSIFICATION.is_valid(classification):
        raise AssertionError(f"{classification} is not a valid classification.")

    return classification
