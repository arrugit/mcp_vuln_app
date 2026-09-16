"""Entry point for running the MCP server as a module: python -m mcp_server"""

import asyncio

from mcp_server.server import mcp

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
