import os
import sys
from pathlib import Path

from dotenv import load_dotenv

dotenv_path = None if "pytest" not in sys.modules else Path(__file__).parent / "test" / ".env.test"
load_dotenv(dotenv_path=dotenv_path)

APP_NAME = os.environ.get("APP_NAME", "howler-dev")
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
HOWLER_URL = os.environ["HOWLER_URL"]
