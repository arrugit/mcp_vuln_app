"""
MCP Service — High-level wrappers for MCP tool calls.

Every function here ultimately calls mcp_client.call_tool().
This is the bridge between FastAPI routers and the MCP server.
Routers should call these functions instead of calling mcp_client directly.
"""

import logging

from backend.mcp_client import mcp_client

logger = logging.getLogger(__name__)


async def read_file(path: str) -> str:
    """
    Read a file via the MCP server's read_file tool.

    Args:
        path: Absolute filesystem path to the file to read.

    Returns:
        File contents as a string.

    Raises:
        RuntimeError: If the MCP client is not connected.
        ValueError: If the MCP server returns an error.
    """
    result = await mcp_client.call_tool("read_file", {"path": path})
    if "error" in result:
        raise ValueError(f"MCP read_file failed: {result['error']}")
    return result.get("content", "")


async def write_file(path: str, content: str) -> bool:
    """
    Write content to a file via the MCP server's write_file tool.

    Args:
        path: Absolute filesystem path to write to.
        content: Content to write.

    Returns:
        True on success.

    Raises:
        ValueError: If the MCP server returns an error.
    """
    result = await mcp_client.call_tool("write_file", {"path": path, "content": content})
    if "error" in result:
        raise ValueError(f"MCP write_file failed: {result['error']}")
    return result.get("success", False)


async def list_files(directory: str) -> list[str]:
    """
    List files in a directory via the MCP server's list_files tool.

    Args:
        directory: Absolute path to the directory to list.

    Returns:
        Sorted list of filenames.

    Raises:
        ValueError: If the MCP server returns an error.
    """
    result = await mcp_client.call_tool("list_files", {"directory": directory})
    if "error" in result:
        raise ValueError(f"MCP list_files failed: {result['error']}")
    return result.get("files", [])


async def search_documents(query: str) -> list[dict[str, str]]:
    """
    Search for documents containing a query string.

    Args:
        query: Search query (case-insensitive).

    Returns:
        List of dicts with "path" and "snippet" keys.
    """
    result = await mcp_client.call_tool("search_documents", {"query": query})
    return result.get("results", [])
