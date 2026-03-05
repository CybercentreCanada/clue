import json
import logging
import sys
import time
from http.client import RemoteDisconnected

import requests
import urllib3
import urllib3.exceptions
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root.addHandler(handler)

ready = False
retries = 0
while not ready and retries < 10:
    keycloak_ready = False
    mongodb_ready = False
    try:
        keycloak = requests.get("http://localhost:9100/health/ready")

        if keycloak.ok:
            data = keycloak.json()
            if data["status"] == "UP" and all(check["status"] == "UP" for check in data["checks"]):
                keycloak_ready = True
            else:
                logging.warning("Keycloak - not up:\n%s", json.dumps(data, indent=2))
        else:
            logging.warning("Keycloak - failed to connect")
    except (
        ConnectionResetError,
        urllib3.exceptions.ProtocolError,
        RemoteDisconnected,
        requests.exceptions.ConnectionError,
    ):
        if retries >= 9:
            logging.exception("Failed to connect to keycloak.")
        else:
            logging.warning("Failed to connect to keycloak, retrying")
    except Exception:
        logging.exception("Exception on network call")

    try:
        client: MongoClient = MongoClient("localhost", 27017, serverSelectionTimeoutMS=5000)
        result = client.admin.command("replSetGetStatus")

        if result.get("ok") == 1:
            mongodb_ready = True
        else:
            logging.warning("MongoDB - replica set not healthy (ok=%s)", result.get("ok"))

        logging.info(
            "Statuses: keycloak=%s, mongodb=%s",
            "ready" if keycloak_ready else "unready",
            "ready" if mongodb_ready else "unready",
        )
        if keycloak_ready and mongodb_ready:
            ready = True
            break
    except (ConnectionFailure, ServerSelectionTimeoutError):
        if retries >= 9:
            logging.exception("Failed to connect to mongodb.")
        else:
            logging.warning("Failed to connect to mongodb, retrying")
    except Exception:
        logging.exception("Exception on network call")

    retries += 1
    time.sleep(5)

if ready:
    logging.info("Keycloak and MongoDB is healthy!")
else:
    logging.critical("Keycloak or MongoDB is unhealthy!")
    sys.exit(1)
