"""
File Tools — MCP server tools for file system operations.

This module provides read_file, write_file, list_files, and search_documents
tools. The read_file tool contains an intentionally vulnerable path-safety
check (MCP02) that uses string-prefix matching without path resolution.

VULNERABILITY (MCP02): The is_path_safe() function checks paths using
exact string-prefix matching against a blacklist. It does NOT resolve
symlinks, canonicalize paths, or resolve relative path components.
This allows bypass via:
  - Relative paths that resolve into blocked directories via OS
  - Symlinks inside allowed directories pointing to blocked targets
"""

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

# Blacklist of directory prefixes that should be blocked.
# This covers common sensitive directories on Linux/macOS.
# NOTE: The application's own data/config/ directory is NOT in this list.
# This is intentional for MCP01 — secrets.env is directly reachable.
BLOCKED_DIRECTORIES: list[str] = ["/etc", "~/.ssh", "/var", "/tmp", "/root"]


def is_path_safe(path: str) -> bool:
    """
    Check if a file path is safe to access.

    Uses exact string-prefix matching against a blacklist of directory names.
    If the path starts with a blocked prefix, access is denied.

    BUG (MCP02): This performs string comparison only. It does NOT:
      - Resolve the path to its canonical form (no os.path.realpath)
      - Follow symlinks to check their targets
      - Resolve relative path components (.., .)
      - Normalize double slashes

    This means:
      - A relative path like "../../etc/passwd" does not literally start
        with "/etc/" as a string, so the check passes.
      - A symlink inside the allowed documents directory whose target
        points to a blocked directory is never detected, because the
        check inspects the symlink's own path, not its resolved target.

    Args:
        path: The file path to check.

    Returns:
        True if the path is considered safe, False if blocked.
    """
    for blocked in BLOCKED_DIRECTORIES:
        if path == blocked or path.startswith(blocked + "/"):
            return False
    return True


def register_file_tools(mcp: MCPServer) -> None:
    """
    Register all file-operation tools on the MCP server instance.

    This function wires up read_file, write_file, list_files, and
    search_documents as MCP tools. The read_file tool contains the
    intentionally vulnerable path-safety check (MCP02).

    Args:
        mcp: The FastMCP server instance to register tools on.
    """

    @mcp.tool()
    async def read_file(path: str) -> dict[str, Any]:
        """
        Read the contents of a file.

        This tool is called by the backend's MCP client to read files on behalf
        of the user. It performs a path-safety check before returning contents.

        VULNERABILITY NOTE (MCP02): The path-safety check uses exact string matching
        against a blacklist. It does NOT resolve path normalization (.., ., //)
        or follow symlinks. This allows relative paths and symlinks to bypass
        the check and access blocked directories.

        Args:
            path: Absolute filesystem path to the file to read.
                  Example: "/home/user/data/uploads/report.txt"

        Returns:
            dict: {"content": str} on success, {"error": str} on failure

        MCP Call Flow:
            Backend -> mcp_client.call_tool("read_file", {"path": path})
            -> JSON-RPC over stdio to MCP server subprocess
            -> This function executes
            -> Response travels back through the same path
        """
        # SECURITY CHECK: verify path is safe before reading
        if not is_path_safe(path):
            return {"error": "Access denied: path is in a restricted directory"}

        # Read and return file contents
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"content": content}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except UnicodeDecodeError:
            return {"error": f"Cannot read binary file: {path}"}

    @mcp.tool()
    async def write_file(path: str, content: str) -> dict[str, Any]:
        """
        Write content to a file.

        Creates the file if it does not exist, overwrites if it does.
        Does NOT perform path-safety checks (write is not the attack vector).

        Args:
            path: Absolute filesystem path to the file to write
            content: Content to write to the file

        Returns:
            dict: {"success": True} on success, {"error": str} on failure
        """
        try:
            # Ensure parent directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except OSError as e:
            return {"error": f"Write failed: {e}"}

    @mcp.tool()
    async def list_files(directory: str) -> dict[str, Any]:
        """
        List files and subdirectories in a directory.

        Returns a flat list of entry names (not full paths).
        Does NOT perform path-safety checks.

        Args:
            directory: Absolute path to the directory to list

        Returns:
            dict: {"files": [list of filenames]} or {"error": str}
        """
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return {"error": f"Directory not found: {directory}"}
            if not dir_path.is_dir():
                return {"error": f"Not a directory: {directory}"}
            entries = [entry.name for entry in dir_path.iterdir()]
            return {"files": sorted(entries)}
        except PermissionError:
            return {"error": f"Permission denied: {directory}"}

    @mcp.tool()
    async def search_documents(query: str) -> dict[str, Any]:
        """
        Search for documents containing a query string.

        Performs case-insensitive text search across all files in the
        uploads directory. Returns matching file paths and a snippet
        of surrounding text.

        Args:
            query: Search query string (case-insensitive)

        Returns:
            dict: {"results": [{"path": str, "snippet": str}]}
        """
        results: list[dict[str, str]] = []
        uploads_dir = Path("data/uploads")
        if not uploads_dir.exists():
            return {"results": results}

        for file_path in uploads_dir.rglob("*"):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if query.lower() in content.lower():
                        # Extract a snippet around the first match
                        idx = content.lower().find(query.lower())
                        start = max(0, idx - 80)
                        end = min(len(content), idx + len(query) + 80)
                        snippet = content[start:end]
                        results.append({
                            "path": str(file_path),
                            "snippet": snippet,
                        })
                except (PermissionError, UnicodeDecodeError):
                    # Skip files we cannot read
                    pass

        return {"results": results}
