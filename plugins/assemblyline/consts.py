import os
from typing import Union

# Clue plugin configuration
DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME", "Assemblyline")
ENABLED_SOURCES = set(os.environ.get("ENABLED_SOURCES", "result|alert|safelist|badlist").split("|"))
ACTIONS_ENABLED = os.environ.get("ACTIONS_ENABLED", "true").lower().strip() == "true"
ICON = os.environ.get("ICON", "mdi:assembly")
CLASSIFICATION = os.environ.get("CLASSIFICATION", "TLP:CLEAR")
PLUGIN_PORT = os.environ.get("PLUGIN_PORT", 8000)

# Assemblyline client configuration
AL_TOKEN_PROVIDER = os.environ.get("AL_TOKEN_PROVIDER", "") # Not needed for assemblyline_client>4.9.12
AL_API_KEY = os.environ.get("AL_API_KEY", "")
AL_USER = os.environ.get("AL_USER", "")
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", 100))
MAX_TIMEOUT = float(os.environ.get("MAX_TIMEOUT", 3))
AL_URL_BASE = os.environ.get("AL_URL_BASE", "https://assemblyline-ui")

verify: Union[str, bool] = str(os.environ.get("VERIFY", "true")).lower()
if verify in ("true", "1"):
    verify = True
elif verify in ("false", "0"):
    verify = False
VERIFY = verify
