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

"""Test cases for the streamable HTTP server entry point."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from analytics_mcp import server_streamable_http
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Mount
from starlette.testclient import TestClient


class TestServerConfig(unittest.TestCase):
    """Tests HTTP server configuration parsing."""

    def test_load_server_config_defaults(self):
        """Defaults should be suitable for a local HTTP server."""
        config = server_streamable_http.load_server_config(
            {},
            env_file=Path("/tmp/google-analytics-mcp-nonexistent.env"),
        )

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.path, "/mcp")

    def test_load_server_config_reads_host_port_and_path(self):
        """Explicit host, port, and path should be honored."""
        config = server_streamable_http.load_server_config(
            {
                "SERVER_HOST": "0.0.0.0",
                "SERVER_PORT": "9000",
                "SERVER_PATH": "/analytics",
            }
        )

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9000)
        self.assertEqual(config.path, "/analytics")

    def test_load_server_config_rejects_invalid_port(self):
        """Invalid ports should fail fast."""
        with self.assertRaises(ValueError):
            server_streamable_http.load_server_config({"SERVER_PORT": "abc"})

    def test_load_server_config_reads_dotenv_file(self):
        """The server should read values from a local .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dotenv_path = Path(tmpdir) / ".env"
            dotenv_path.write_text(
                "SERVER_HOST=0.0.0.0\n"
                "SERVER_PORT=9100\n"
                "SERVER_PATH=/from-dotenv\n",
                encoding="utf-8",
            )

            config = server_streamable_http.load_server_config(
                {},
                env_file=dotenv_path,
            )

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9100)
        self.assertEqual(config.path, "/from-dotenv")

    def test_env_overrides_dotenv_file(self):
        """Process env should override .env values when both are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dotenv_path = Path(tmpdir) / ".env"
            dotenv_path.write_text(
                "SERVER_HOST=0.0.0.0\n"
                "SERVER_PORT=9100\n"
                "SERVER_PATH=/from-dotenv\n",
                encoding="utf-8",
            )

            config = server_streamable_http.load_server_config(
                {
                    "SERVER_HOST": "127.0.0.1",
                    "SERVER_PORT": "9200",
                    "SERVER_PATH": "/from-env",
                },
                env_file=dotenv_path,
            )

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 9200)
        self.assertEqual(config.path, "/from-env")


class TestStreamableHTTPApp(unittest.TestCase):
    """Tests HTTP app construction."""

    def test_create_streamable_http_app_mounts_configured_path(self):
        """The ASGI app should mount the configured MCP path."""
        config = server_streamable_http.load_server_config(
            {"SERVER_PATH": "/analytics-mcp"}
        )

        app = server_streamable_http.create_streamable_http_app(config)

        mount_paths = [route.path for route in app.app.routes]
        self.assertIn("/analytics-mcp", mount_paths)

    def test_direct_path_wrapper_avoids_redirect_for_exact_path(self):
        """Posting to /mcp should not trigger a redirect to /mcp/."""

        async def transport_app(scope, receive, send):
            response = PlainTextResponse("ok")
            await response(scope, receive, send)

        app = Starlette(routes=[Mount("/mcp", app=transport_app)])
        wrapped = server_streamable_http.DirectPathTransportWrapper(
            app, "/mcp"
        )

        client = TestClient(wrapped)
        response = client.post("/mcp", data="{}", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get("location"))
        self.assertEqual(response.text, "ok")


class TestRunServer(unittest.TestCase):
    """Tests server startup wiring."""

    def test_run_server_uses_asyncio_run(self):
        """The synchronous entry point should delegate to asyncio.run."""
        with (
            patch(
                "analytics_mcp.server_streamable_http.asyncio.run"
            ) as asyncio_run,
            patch(
                "analytics_mcp.server_streamable_http.run_server_async",
                new=lambda: "sentinel-coro",
            ),
        ):
            server_streamable_http.run_server()

        asyncio_run.assert_called_once_with("sentinel-coro")
