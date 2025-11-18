import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_pythonpath(pytestconfig):
    """Adds command line folders to the Python path.

    Args:
        pytestconfig (pytest.Config): The pytest configuration object containing command-line args.

    Returns:
        None
    """
    for _path in pytestconfig.args:
        folder = Path(_path)
        if folder.exists() and folder.is_dir():
            sys.path.append(str(folder))
