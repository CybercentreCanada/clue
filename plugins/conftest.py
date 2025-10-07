import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def inject_paths(pytestconfig):
    """Injects specified paths into sys.path for pytest session.

    Args:
        pytestconfig (_pytest.config.Config): The pytest configuration object
            containing command-line arguments.
    """
    for _path in pytestconfig.args:
        folder = Path(_path).resolve()

        if folder.exists():
            sys.path.insert(0, str(folder))

    try:
        import clue  # noqa: F401
    except ImportError:
        clue_folder = (Path(__file__).parent.parent / "api").resolve()
        sys.path.append(str(clue_folder))
        sys.path.append(str(clue_folder / f".venv/lib/python3.{sys.version_info.minor}/site-packages"))
