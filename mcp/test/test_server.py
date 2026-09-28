from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from starlette.applications import Starlette

from clue_mcp.config import CLUE_API
from clue_mcp.server import _with_api_client_lifespan


@pytest.mark.asyncio
async def test_api_client_closes_with_http_app_lifespan():
    lifecycle_events: list[str] = []

    @asynccontextmanager
    async def app_lifespan(_: Starlette):
        lifecycle_events.append("started")
        try:
            yield
        finally:
            lifecycle_events.append("stopped")

    app = Starlette(lifespan=app_lifespan)
    api_client = AsyncMock()
    wrapped_app = _with_api_client_lifespan(app, api_client)

    async with wrapped_app.router.lifespan_context(wrapped_app):
        assert lifecycle_events == ["started"]
        api_client.start.assert_awaited_once()
        api_client.aclose.assert_not_awaited()

    assert lifecycle_events == ["started", "stopped"]
    start_call = api_client.start.await_args
    assert start_call is not None
    limits = start_call.kwargs["limits"]
    assert limits.max_connections == CLUE_API.MAX_CONNECTIONS
    assert limits.max_keepalive_connections == CLUE_API.MAX_KEEPALIVE_CONNECTIONS
    assert limits.keepalive_expiry == CLUE_API.KEEPALIVE_EXPIRY
    api_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_client_closes_if_startup_fails():
    app_lifespan_started = False

    @asynccontextmanager
    async def app_lifespan(_: Starlette):
        nonlocal app_lifespan_started
        app_lifespan_started = True
        yield

    app = Starlette(lifespan=app_lifespan)
    api_client = AsyncMock()
    api_client.start.side_effect = RuntimeError("client startup failed")
    wrapped_app = _with_api_client_lifespan(app, api_client)

    with pytest.raises(RuntimeError, match="client startup failed"):
        async with wrapped_app.router.lifespan_context(wrapped_app):
            pass

    assert not app_lifespan_started
    api_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_client_closes_if_application_shutdown_fails():
    @asynccontextmanager
    async def app_lifespan(_: Starlette):
        yield
        raise RuntimeError("application shutdown failed")

    app = Starlette(lifespan=app_lifespan)
    api_client = AsyncMock()
    wrapped_app = _with_api_client_lifespan(app, api_client)

    with pytest.raises(RuntimeError, match="application shutdown failed"):
        async with wrapped_app.router.lifespan_context(wrapped_app):
            pass

    api_client.aclose.assert_awaited_once()
