from __future__ import annotations

from typing import Any


class MCPv2ClientAdapter:
    """Thin optional adapter for discovering/calling a remote MCP v2 server.

    This module intentionally keeps governance metadata separate: MCP schemas
    tell PBME what a tool can accept/return, while the governance catalog
    tells PBME what may be disclosed for a purpose.
    """

    def __init__(self, url: str):
        self.url = url

    async def list_tools(self) -> list[dict[str, Any]]:
        from mcp import Client

        async with Client(self.url) as client:
            result = await client.list_tools()
            return [
                {
                    "name": tool.name,
                    "title": tool.title,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "output_schema": getattr(tool, "output_schema", None),
                }
                for tool in result.tools
            ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> Any:
        from mcp import Client

        async with Client(self.url) as client:
            result = await client.call_tool(name, arguments)
            if result.is_error:
                raise RuntimeError(f"Downstream MCP tool failed: {name}")
            if result.structured_content is not None:
                return result.structured_content
            return result.content
