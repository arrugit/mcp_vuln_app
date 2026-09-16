"""
VULNEX MCP Server — Standalone MCP server for file operations.

This server runs as a separate process and communicates via stdio.
It is spawned by the backend as a subprocess and is NOT imported
directly by any backend code.

Can be tested independently with:
  - MCP Inspector: npx @modelcontextprotocol/inspector uv run python -m
    mcp_server.server
  - Direct: echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' |
    uv run python -m mcp_server.server
"""

import asyncio

from mcp.server.mcpserver import MCPServer

# Create the MCP server instance
mcp = MCPServer("vulnex-mcp-server")

# Import tool registrations from the file_tools module
# E402: import placed after mcp instance creation to avoid circular import
from mcp_server.file_tools import register_file_tools  # noqa: E402

# Wire up all file-operation tools to the server
register_file_tools(mcp)

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
