# VULNEX — Architecture & Conventions Reference

## Project Overview

VULNEX is an AI-powered productivity assistant (document management, task tracking, calendar/scheduling) built as a university final-year project on AI/MCP application security. It contains three intentionally embedded vulnerabilities that reproduce real-world MCP/AI security bug patterns.

## Architecture

```
Frontend (HTMX + Alpine.js + Jinja2, no build step)
        | served by FastAPI, port 8005
Backend (FastAPI + SQLAlchemy + SQLite)
  - app logic, auth, CRUD
  - MCP CLIENT only -- spawns MCP server as subprocess
        | JSON-RPC over stdio (MCP protocol)
MCP Server (official mcp Python SDK, FastMCP)
  - standalone process, independently launchable
  - exposes tools via @mcp.tool()
  - holds ALL vulnerability logic
```

## Critical Rule: MCP Boundary

**The backend MUST NEVER import any function from `mcp_server/` directly.** Every file/document operation goes through a real MCP protocol call via `ClientSession.call_tool()`.

- `mcp_server/` is a separate Python package
- `backend/mcp_client.py` spawns the server as a subprocess
- No `sys.path` manipulation or cross-package imports

## Directory Structure

```
vulnex/
  CLAUDE.md
  PRD.md
  TDD.md
  pyproject.toml
  backend/
    main.py              # FastAPI app entrypoint
    mcp_client.py        # MCP client (subprocess + ClientSession)
    llm_client.py        # Ollama integration (MCP06)
    models.py            # SQLAlchemy models
    schemas.py           # Pydantic schemas
    routers/
      documents.py       # Document CRUD + summarization
      tasks.py           # Task CRUD
      calendar.py        # Calendar endpoints
    services/
      document_service.py
      task_service.py
      mcp_service.py     # High-level MCP call wrappers
      summarization_service.py  # Ollama + MCP tool-call orchestration
    templates/
      base.html
      documents.html
      tasks.html
      calendar.html
    static/
      css/
        style.css
  mcp_server/
    __init__.py
    __main__.py
    server.py            # FastMCP server with @mcp.tool() definitions
    file_tools.py        # File tools with vulnerable path check (MCP02)
  data/
    vulnex.db            # SQLite database (created at runtime)
    uploads/             # User-uploaded documents
    config/
      secrets.env        # Application secrets (MCP01 target)
  exploits/
    mcp02_path_traversal.md
    mcp01_secret_exposure.md
    mcp06_prompt_injection.md
```

## Tech Stack

- **Package manager:** uv only (no Docker, no pip, no poetry)
- **Python:** 3.11+
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** HTMX 1.9+ + Alpine.js 3.x + Jinja2 (no build step)
- **MCP SDK:** Official `mcp` Python package, `FastMCP` for server, `ClientSession` for client
- **MCP Transport:** stdio only
- **LLM Runtime:** Local Ollama instance, model `llama3.2:3b` (configurable via `VULNEX_OLLAMA_MODEL`)
- **Port:** 8005

## Code Conventions

- **Python:** PEP 8, enforced by ruff
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all functions, classes, modules; Google-style
- **Comments:** Heavy -- every function should be understandable in isolation
- **File naming:** `snake_case.py` for Python, `snake_case.html` for templates
- **Exploit docs:** `mcp{ID}_{short_name}.md`
- **Commit messages:** `<type>(<scope>): <description>` (e.g., `feat(mcp-server): add read_file tool`)

## Vulnerabilities

| ID | Name | Location | Bug Category |
|----|------|----------|-------------|
| MCP02 | Path Traversal Blacklist Bypass | `mcp_server/file_tools.py` | String-prefix path check without resolution |
| MCP01 | Secret Exposure | `data/config/secrets.env` | Sensitive file not in blacklist |
| MCP06 | Indirect Prompt Injection | `backend/llm_client.py` + `backend/services/summarization_service.py` | Untrusted document content sent to LLM |

## Running

```bash
# Install dependencies
uv sync

# Run the app
uv run uvicorn backend.main:app --reload --port 8005

# Run MCP server standalone
uv run python -m mcp_server.server

# MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m mcp_server.server

# Lint
uv run ruff check .
```
