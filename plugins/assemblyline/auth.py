from contextlib import contextmanager
from importlib.metadata import version
from typing import TYPE_CHECKING

import assemblyline_client
from clue.common.exceptions import ClueRuntimeError
from clue.common.logging import get_logger
from consts import AL_API_KEY, AL_TOKEN_PROVIDER, AL_URL_BASE, AL_USER, VERIFY
from flask import request
from packaging.version import parse

if TYPE_CHECKING:
    pass


logger = get_logger(__file__)
CLIENT_VERSION = parse(version("assemblyline_client"))


@contextmanager
def get_assemblyline_client():
    """Context manager to provide an Assemblyline client with token exchange for OBO (On-Behalf-Of) authentication or API key."""  # noqa: E501
    client = None
    try:
        # If API key and user are provided, use them to create the client
        if AL_API_KEY and AL_USER:
            client = assemblyline_client.get_client(AL_URL_BASE, apikey=(AL_USER, AL_API_KEY), verify=VERIFY)  # type: ignore
        elif request.headers.get("authorization"):
            # If no API key is provided, attempt to perform token exchange using the token from the request header
            token = request.headers["authorization"].split(" ")[-1]

            # Take token from request header from Clue and perform a token exchange for Assemblyline
            if CLIENT_VERSION <= parse("4.9.12"):
                # Use token provider for older client versions
                client = assemblyline_client.get_client(AL_URL_BASE, oauth=(AL_TOKEN_PROVIDER, token), verify=VERIFY)  # type: ignore
            else:
                # Newer version of the client is able to infer the token provider from the token itself, so we can just pass the token directly # noqa: E501
                client = assemblyline_client.get_client(AL_URL_BASE, oauth=token, verify=VERIFY)  # type: ignore

        if client:
            yield client, client.get_classification_engine()
        else:
            logger.warning("Client is not set!")
            raise ClueRuntimeError("Client not initialized, request was unsuccessful.")
    finally:
        if client:
            # Close the client session to free up resources
            client._connection.session.close()  # type: ignore
