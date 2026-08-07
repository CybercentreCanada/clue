from contextlib import contextmanager
from typing import TYPE_CHECKING

from assemblyline_client import get_client
from clue.common.exceptions import ClueRuntimeError
from clue.common.logging import get_logger
from flask import request

from .consts import AL_API_KEY, AL_URL_BASE, AL_USER, VERIFY

if TYPE_CHECKING:
    pass


logger = get_logger(__file__)


@contextmanager
def get_assemblyline_client():
    """Context manager to provide an Assemblyline client with token exchange for OBO (On-Behalf-Of) authentication or API key."""
    client = None
    try:
        # If API key and user are provided, use them to create the client
        if AL_API_KEY and AL_USER:
            client = get_client(AL_URL_BASE, apikey=(AL_USER, AL_API_KEY), verify=VERIFY)  # type: ignore
        else:
            # If no API key is provided, attempt to perform token exchange using the token from the request header
            token = request.headers.get("authorization", "").split(" ")[-1]

            # Take token from request header from Clue and perform a token exchange for Assemblyline
            client = get_client(AL_URL_BASE, oauth=token, verify=VERIFY)  # type: ignore

        if client:
            yield client, client.get_classification_engine()
        else:
            logger.warning("Client is not set!")
            raise ClueRuntimeError("Client not initialized, request was unsuccessful.")
    finally:
        if client:
            # Close the client session to free up resources
            client._connection.session.close()  # type: ignore
