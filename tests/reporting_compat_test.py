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

"""Compatibility tests for reporting tool inputs."""

import unittest
from unittest.mock import AsyncMock, patch

from analytics_mcp import coordinator
from analytics_mcp.tools.reporting import core, realtime


class TestReportingInputCompatibility(unittest.IsolatedAsyncioTestCase):
    """Tests compatibility with both string and object item formats."""

    def test_run_report_schema_accepts_named_object_items(self):
        """run_report should accept dimension/metric objects with names."""
        tool = next(
            tool for tool in coordinator.mcp_tools if tool.name == "run_report"
        )

        dimension_schema = tool.inputSchema["properties"]["dimensions"][
            "items"
        ]
        metric_schema = tool.inputSchema["properties"]["metrics"]["items"]

        self.assertIn("anyOf", dimension_schema)
        self.assertIn("anyOf", metric_schema)

    def test_run_realtime_report_schema_accepts_named_object_items(self):
        """run_realtime_report should accept dimension/metric objects."""
        tool = next(
            tool
            for tool in coordinator.mcp_tools
            if tool.name == "run_realtime_report"
        )

        dimension_schema = tool.inputSchema["properties"]["dimensions"][
            "items"
        ]
        metric_schema = tool.inputSchema["properties"]["metrics"]["items"]

        self.assertIn("anyOf", dimension_schema)
        self.assertIn("anyOf", metric_schema)

    async def test_run_report_normalizes_named_object_items(self):
        """run_report should normalize object items into string names."""
        response = AsyncMock(return_value=object())
        client = AsyncMock()
        client.run_report = response

        with (
            patch.object(core, "create_data_api_client", return_value=client),
            patch.object(
                core, "proto_to_dict", return_value={"ok": True}
            ),
        ):
            result = await core.run_report(
                property_id="397835205",
                date_ranges=[
                    {
                        "start_date": "2026-03-16",
                        "end_date": "2026-03-22",
                        "name": "W12",
                    }
                ],
                dimensions=[{"name": "sessionDefaultChannelGroup"}],
                metrics=[{"name": "sessions"}, {"name": "bounceRate"}],
            )

        request = response.await_args.args[0]
        self.assertEqual(
            [dimension.name for dimension in request.dimensions],
            ["sessionDefaultChannelGroup"],
        )
        self.assertEqual(
            [metric.name for metric in request.metrics],
            ["sessions", "bounceRate"],
        )
        self.assertEqual(result, {"ok": True})

    async def test_run_realtime_report_normalizes_named_object_items(self):
        """run_realtime_report should normalize object items into names."""
        response = AsyncMock(return_value=object())
        client = AsyncMock()
        client.run_realtime_report = response

        with (
            patch.object(
                realtime, "create_data_api_client", return_value=client
            ),
            patch.object(
                realtime, "proto_to_dict", return_value={"ok": True}
            ),
        ):
            result = await realtime.run_realtime_report(
                property_id="397835205",
                dimensions=[{"name": "country"}],
                metrics=[{"name": "activeUsers"}],
            )

        request = response.await_args.args[0]
        self.assertEqual(
            [dimension.name for dimension in request.dimensions],
            ["country"],
        )
        self.assertEqual(
            [metric.name for metric in request.metrics],
            ["activeUsers"],
        )
        self.assertEqual(result, {"ok": True})
