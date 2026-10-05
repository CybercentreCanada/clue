import re

from clue.common.exceptions import ClueValueError
from clue.config import CLASSIFICATION


def validate_plugin_identifier(value: str) -> str:
    """Allow safe ASCII components separated by dots, never dot segments."""
    if re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", value) is None:
        raise ClueValueError("Invalid plugin identifier.", status_code=400)
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
