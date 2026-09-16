"""
MCP Client — Subprocess manager and JSON-RPC transport for the MCP server.

This module is the ONLY part of the backend that communicates with the MCP server.
It spawns the server as a subprocess, manages the ClientSession, and provides
a call_tool() method for invoking MCP tools.

CRITICAL: This module NEVER imports from mcp_server/. All communication goes
through the MCP protocol over stdio (JSON-RPC 2.0).
"""

import logging
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP client that spawns and communicates with the MCP server subprocess.

    Manages the full lifecycle: subprocess spawn, session initialization,
    tool invocation, and graceful shutdown. Uses the official mcp Python SDK
    for protocol handling.
    """

    def __init__(self) -> None:
        """Initialize the MCP client with no active connection."""
        self._session: ClientSession | None = None
        self._session_context: Any = None
        self._read_write_context: Any = None

    async def start(self) -> None:
        """
        Spawn the MCP server subprocess and establish a ClientSession.

        This method:
        1. Creates a StdioServerParameters pointing to mcp_server.server
        2. Opens a stdio transport connection to the subprocess
        3. Creates and initializes a ClientSession
        4. Stores the session for later use by call_tool()

        The subprocess runs: python -m mcp_server.server
        """
        logger.info("Starting MCP server subprocess...")

        # Parameters for spawning the MCP server process
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server.server"],
        )

        # Open stdio transport — spawns subprocess and connects stdin/stdout
        self._read_write_context = stdio_client(server_params)
        read_stream, write_stream = await self._read_write_context.__aenter__()

        # Create and initialize the MCP session
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()

        logger.info("MCP server started and session initialized.")

    async def stop(self) -> None:
        """
        Gracefully shut down the MCP server subprocess.

        Closes the ClientSession and the stdio transport, which terminates
        the subprocess. Logs warnings if shutdown encounters errors.
        """
        logger.info("Stopping MCP server...")

        try:
            if self._session_context is not None:
                await self._session_context.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("Error closing MCP session: %s", e)

        try:
            if self._read_write_context is not None:
                await self._read_write_context.__aexit__(None, None, None)
        except Exception as e:
            logger.warning("Error closing stdio transport: %s", e)

        self._session = None
        self._session_context = None
        self._read_write_context = None
        logger.info("MCP server stopped.")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call an MCP tool and return the result.

        This is the primary interface for invoking tools on the MCP server.
        It serializes the request as a JSON-RPC call over the stdio transport,
        waits for the response, and returns the parsed result.

        Args:
            tool_name: Name of the tool (e.g., "read_file", "list_files")
            arguments: Tool arguments as a dict (e.g., {"path": "/some/path"})

        Returns:
            Tool response as a dict. For read_file: {"content": str}.
            For errors: {"error": str}.

        Raises:
            RuntimeError: If the client is not connected to a server.
            Exception: If the MCP protocol call fails.
        """
        if self._session is None:
            raise RuntimeError("MCP client is not connected. Call start() first.")

        logger.debug("MCP call_tool: %s(%s)", tool_name, arguments)

        result = await self._session.call_tool(tool_name, arguments)

        # The MCP SDK returns a CallToolResult with a list of content items.
        # Extract the text content from the first item.
        if result.content and len(result.content) > 0:
            content_item = result.content[0]
            # TextContent has a .text attribute
            if hasattr(content_item, "text"):
                import json
                try:
                    return json.loads(content_item.text)
                except (json.JSONDecodeError, TypeError):
                    return {"content": content_item.text}

        return {"error": "No content in MCP tool response"}


# Module-level singleton — imported by routers and services
mcp_client = MCPClient()
