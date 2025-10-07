import sys
from pathlib import Path

folder = Path(sys.argv[1]).resolve()

sys.path.insert(0, str(folder))
