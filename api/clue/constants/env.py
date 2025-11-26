import os

DISABLE_CACHE = os.environ.get("DISABLE_CACHE", "false").lower() in ["true", "1"]
TESTING = os.environ.get("TESTING", "false").lower() in ["true", "1"]
