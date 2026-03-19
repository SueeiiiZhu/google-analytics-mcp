#!/usr/bin/env python

# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Streamable HTTP entry point for the Google Analytics MCP server."""

import asyncio
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import anyio
import analytics_mcp.coordinator as coordinator
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route
import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_PATH = "/mcp"
DEFAULT_ENV_FILE = ".env"


@dataclass(frozen=True)
class ServerConfig:
    """Configuration for the streamable HTTP server."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    path: str = DEFAULT_PATH


def _normalize_path(path: str) -> str:
    """Normalizes the MCP endpoint path."""
    path = (path or DEFAULT_PATH).strip()
    if not path:
        return DEFAULT_PATH
    if not path.startswith("/"):
        path = f"/{path}"
    return path.rstrip("/") or "/"


def load_dotenv_file(env_file: str | Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Loads simple KEY=VALUE pairs from a .env file."""
    path = Path(env_file)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def load_server_config(
    env: Mapping[str, str] | None = None,
    env_file: str | Path = DEFAULT_ENV_FILE,
) -> ServerConfig:
    """Loads HTTP server config from environment variables."""
    merged_env = load_dotenv_file(env_file)
    merged_env.update(os.environ if env is None else env)

    port_value = merged_env.get("SERVER_PORT", str(DEFAULT_PORT))
    try:
        port = int(port_value)
    except ValueError as exc:
        raise ValueError("SERVER_PORT must be an integer") from exc

    return ServerConfig(
        host=merged_env.get("SERVER_HOST", DEFAULT_HOST),
        port=port,
        path=_normalize_path(merged_env.get("SERVER_PATH", DEFAULT_PATH)),
    )


def create_initialization_options() -> InitializationOptions:
    """Builds MCP initialization options for this server."""
    return InitializationOptions(
        server_name=coordinator.app.name,
        server_version="1.0.0",
        capabilities=coordinator.app.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


class StreamableHTTPHandler:
    """ASGI adapter for the MCP streamable HTTP transport."""

    def __init__(self, transport: StreamableHTTPServerTransport):
        self.transport = transport

    async def __call__(self, scope, receive, send):
        await self.transport.handle_request(scope, receive, send)


class DirectPathTransportWrapper:
    """Allows exact MCP paths like /mcp without a redirect to /mcp/."""

    def __init__(self, app, path: str):
        self.app = app
        self.path = path

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] == "http"
            and self.path != "/"
            and scope["path"] == self.path
        ):
            scope = dict(scope)
            rewritten_path = f"{self.path}/"
            scope["path"] = rewritten_path
            scope["raw_path"] = rewritten_path.encode("utf-8")
        await self.app(scope, receive, send)


async def _healthcheck(_request):
    """Simple endpoint for liveness checks."""
    return PlainTextResponse("ok")


def create_streamable_http_app(config: ServerConfig) -> Starlette:
    """Creates the ASGI app for streamable HTTP transport."""
    transport = StreamableHTTPServerTransport(mcp_session_id=None)
    handler = StreamableHTTPHandler(transport)

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        async with transport.connect() as (read_stream, write_stream):
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(
                    coordinator.app.run,
                    read_stream,
                    write_stream,
                    create_initialization_options(),
                )
                yield
                task_group.cancel_scope.cancel()

    app = Starlette(
        routes=[
            Route("/healthz", _healthcheck, methods=["GET"]),
            Mount(config.path, app=handler),
        ],
        lifespan=lifespan,
    )
    return DirectPathTransportWrapper(app, config.path)


async def run_server_async(config: ServerConfig | None = None):
    """Runs the MCP server over streamable HTTP."""
    config = load_server_config() if config is None else config
    app = create_streamable_http_app(config)
    print(
        "Starting MCP Streamable HTTP Server:",
        coordinator.app.name,
        f"at http://{config.host}:{config.port}{config.path}",
    )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.host,
            port=config.port,
            log_level="info",
        )
    )
    await server.serve()


def run_server():
    """Synchronous wrapper to run the async HTTP server."""
    asyncio.run(run_server_async())


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nMCP Streamable HTTP Server stopped by user.")
    except Exception:
        print("MCP Streamable HTTP Server encountered an error:")
        raise
