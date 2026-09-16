"""
Secrets Router — API endpoints for application secrets management.

VULNERABILITY (MCP01): This router exposes application secrets stored in
data/config/secrets.env. The secrets file is read via the MCP server's
read_file tool. Because data/config/ is NOT in the MCP server's
BLOCKED_DIRECTORIES list, the file is directly accessible.

The /api/secrets/ endpoint lists all secrets.
The /api/secrets/{key} endpoint reads a specific secret's value.
Both endpoints go through the MCP server's read_file tool.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.services import mcp_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Path to the secrets file (relative to project root)
SECRETS_FILE = Path(__file__).parent.parent.parent / "data" / "config" / "secrets.env"


def _parse_secrets(content: str) -> dict[str, str]:
    """
    Parse a .env file into a dictionary of key-value pairs.

    Lines starting with # are comments. Empty lines are skipped.
    Values containing = are split on the first = only.

    Args:
        content: The raw .env file content.

    Returns:
        Dictionary of secret key-value pairs.
    """
    secrets: dict[str, str] = {}
    for line in content.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            secrets[key.strip()] = value.strip()
    return secrets


@router.get("/")
async def list_secrets() -> dict[str, str]:
    """
    List all application secrets.

    Reads the secrets.env file via the MCP server's read_file tool
    and returns all key-value pairs. Secret values are masked in the
    response for the list endpoint.

    VULNERABILITY (MCP01): The MCP server's read_file tool can read
    data/config/secrets.env because this path is not in BLOCKED_DIRECTORIES.
    """
    try:
        content = await mcp_service.read_file(str(SECRETS_FILE))
    except Exception as e:
        logger.error("Failed to read secrets file: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to read secrets file",
        )

    secrets = _parse_secrets(content)
    # Mask values for the list endpoint
    masked = {}
    for key, value in secrets.items():
        if len(value) > 4:
            masked[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
        else:
            masked[key] = "****"
    return masked


@router.get("/{key}")
async def get_secret(key: str) -> dict[str, str]:
    """
    Read a specific secret value by key.

    Returns the full, unmasked value of the requested secret.

    VULNERABILITY (MCP01): This endpoint exposes raw secret values.
    An attacker who knows (or guesses) a key name can retrieve the
    full secret through the MCP server.
    """
    try:
        content = await mcp_service.read_file(str(SECRETS_FILE))
    except Exception as e:
        logger.error("Failed to read secrets file: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to read secrets file",
        )

    secrets = _parse_secrets(content)
    if key not in secrets:
        raise HTTPException(
            status_code=404,
            detail=f"Secret '{key}' not found",
        )

    return {"key": key, "value": secrets[key]}
