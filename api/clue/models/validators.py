from clue.config import CLASSIFICATION


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
