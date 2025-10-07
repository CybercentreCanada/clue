import sys
from pathlib import Path

folder = Path(sys.argv[1]).resolve()

sys.path.insert(0, str(folder))

try:
    import clue  # noqa: F401
except ImportError:
    clue_folder = (Path(__file__).parent.parent / "api").resolve()
    sys.path.append(str(clue_folder))
    sys.path.append(str(clue_folder / f".venv/lib/python3.{sys.version_info.minor}/site-packages"))
