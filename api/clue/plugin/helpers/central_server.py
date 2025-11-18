# import os

# from clue_client import get_client
# from clue_client.api.v1 import V1
# from flask import request

# from clue.common.logging import get_logger

# CENTRAL_SERVER_URL = os.getenv("CENTRAL_API_URL", "http://enrichment-rest.enrichment.svc.cluster.local:5000")

# logger = get_logger(__file__)


# def connect_to_central_server(timeout: int | None = 3, retries: int = 3) -> V1:
#     "Connect to the central server using the clue client"
#     access_token = request.headers.get("X-Clue-Authorization", None)

#     if access_token:
#         logger.info("X-Clue-Authorization header specified, using pre-OBO token")
#     else:
#         logger.warning("X-Clue-Authorization header not specified, falling back to core Authorization Header")
#         access_token = request.headers.get("Authorization", " ", type=str).split(" ")[1]

#     if not access_token:
#         logger.warning("No token specified, continuing with no authentication")

#   return get_client(CENTRAL_SERVER_URL, auth=access_token, version=1, timeout=timeout, retries=retries, logger=logger)
