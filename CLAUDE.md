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
MCP Server (official mcp Python SDK, MCPServer v2)
  - standalone process, independently launchable
  - exposes tools via @server.tool()
  - holds ALL vulnerability logic
```

## Critical Rule: MCP Boundary

**The backend MUST NEVER import any function from `mcp_server/` directly.** Every file/document operation goes through a real MCP protocol call via `ClientSession.call_tool()`.

- `mcp_server/` is a separate Python package
- `backend/mcp_client.py` spawns the server as a subprocess
- No `sys.path` manipulation or cross-package imports

---

## File-by-File Summary

### `backend/`

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entrypoint. Manages lifespan (database init, MCP server spawn/stop, default user seeding). Mounts static files, includes API routers, serves page templates. |
| `mcp_client.py` | **Only module that talks to the MCP server.** `MCPClient` class spawns `mcp_server.server` as subprocess via `asyncio`, manages `ClientSession`, provides `call_tool(tool_name, arguments) → dict`. Module-level singleton `mcp_client`. |
| `llm_client.py` | Ollama HTTP client. `LLMClient` class calls Ollama's `/api/generate` endpoint using stdlib `urllib.request`. Configurable via `VULNEX_OLLAMA_URL` and `VULNEX_OLLAMA_MODEL` env vars. Module-level singleton `llm_client`. |
| `database.py` | SQLAlchemy async engine for SQLite (`data/vulnex.db`). `get_db()` dependency for FastAPI route injection. |
| `models.py` | SQLAlchemy ORM models: `User`, `Folder`, `Document`, `Task`, `TaskComment`, `Event`. |
| `schemas.py` | Pydantic request/response schemas for all API endpoints. |
| `routers/documents.py` | Document CRUD: list (JSON + HTML partial), get, upload (multipart), view content (via MCP `read_file`), search, delete, summarize (placeholder). HTML partial endpoint for HTMX document grid. |
| `routers/tasks.py` | Task CRUD: list (with filters), get, create, update (PATCH), kanban status update, comments, delete. |
| `routers/calendar.py` | Calendar: list events (includes tasks with due dates), get, create, delete. |
| `routers/secrets.py` | Application secrets: list all (masked), read specific key (full value). Reads `data/config/secrets.env` via MCP `read_file` tool (MCP01 vulnerability). |
| `services/document_service.py` | Document business logic. `get_document_content()` constructs full path and calls `mcp_service.read_file()`. |
| `services/task_service.py` | Task business logic: CRUD, filtering, comment management. |
| `services/mcp_service.py` | High-level wrappers: `read_file()`, `write_file()`, `list_files()`, `search_documents()`. All call `mcp_client.call_tool()`. |
| `services/summarization_service.py` | AI summarization via Ollama. Accepts document content, builds prompt, calls `llm_client.generate()`. Vulnerable to MCP06 — document content injected into prompt without sanitization. |
| `templates/base.html` | Jinja2 base template. CDN links for HTMX 1.9 + Alpine.js 3.x. Left sidebar nav. |
| `templates/documents.html` | Document list grid (HTMX partial loading), upload modal, document viewer panel, summary panel. |
| `templates/_doc_cards.html` | HTMX partial for document cards — rendered by `/api/documents/partial/list`. |
| `templates/tasks.html` | Kanban board (4 columns), task creation modal, HTMX-driven task loading. |
| `templates/calendar.html` | Monthly calendar grid, event creation modal, prev/next/today navigation. |
| `templates/secrets.html` | Application configuration page. Lists secrets from `data/config/secrets.env` via MCP. Reveal buttons to show full values. |
| `static/css/style.css` | Global styles. Muted SaaS color palette (blue primary, off-white bg, green accent). |

### `mcp_server/`

| File | Purpose |
|------|---------|
| `server.py` | Creates `MCPServer("vulnex-mcp-server")` instance. Imports and registers tools from `file_tools`. Runs stdio transport via `asyncio.run(mcp.run_stdio_async())`. |
| `file_tools.py` | `register_file_tools(mcp)` wires up 4 tools: `read_file` (vulnerable — MCP02), `write_file`, `list_files`, `search_documents`. Contains `is_path_safe()` with the intentionally flawed blacklist check. |
| `__main__.py` | Entry point for `python -m mcp_server`. Calls `asyncio.run(mcp.run_stdio_async())`. |
| `__init__.py` | Package marker. |

### `data/`

| Path | Purpose |
|------|---------|
| `uploads/` | User-uploaded documents (created at runtime). |
| `config/` | Application config directory. `secrets.env` contains fake API keys and credentials (MCP01 target). |
| `vulnex.db` | SQLite database (created at runtime on first start). |

---

## MCP Protocol Flow

```
1. User action in UI (e.g., view document)
2. HTMX request → FastAPI router
3. Router calls service (e.g., document_service.get_document_content())
4. Service calls mcp_service.read_file(path)
5. mcp_service calls mcp_client.call_tool("read_file", {"path": path})
6. mcp_client serializes to JSON-RPC, writes to subprocess stdin
7. mcp_server/file_tools.py read_file() executes
8. Response travels back: server → stdout → mcp_client → mcp_service → service → router → HTTP
```

## MCP Tool Inventory

| Tool | Parameters | Returns | Vulnerable? |
|------|-----------|---------|-------------|
| `read_file` | `path: str` | `{"content": str}` | **Yes — MCP02** (blacklist bypass) |
| `write_file` | `path: str, content: str` | `{"success": bool}` | No |
| `list_files` | `directory: str` | `{"files": list[str]}` | No |
| `search_documents` | `query: str` | `{"results": list[dict]}` | No |

---

## Vulnerabilities

| ID | Name | Location | Status |
|----|------|----------|--------|
| MCP02 | Path Traversal Blacklist Bypass | `mcp_server/file_tools.py` (`is_path_safe()`) | **Done** — live through document viewer, exploit doc written |
| MCP01 | Secret Exposure | `data/config/secrets.env` | **Done** — live through Config page, exploit doc written |
| MCP06 | Indirect Prompt Injection | `backend/llm_client.py` + `backend/services/summarization_service.py` | **Done** — live through document summarization, exploit doc written |

---

## Tech Stack

- **Package manager:** uv only (no Docker, no pip, no poetry)
- **Python:** 3.11+
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** HTMX 1.9+ + Alpine.js 3.x + Jinja2 (no build step)
- **MCP SDK:** `mcp` Python package v2 (`MCPServer` for server, `ClientSession` for client)
- **MCP Transport:** stdio only
- **LLM Runtime (Phase 4):** Local Ollama, model `llama3.2:3b` (configurable via `VULNEX_OLLAMA_MODEL`)
- **Port:** 8005

## Code Conventions

- **Python:** PEP 8, enforced by ruff
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all functions, classes, modules; Google-style
- **Comments:** Heavy — every function should be understandable in isolation
- **File naming:** `snake_case.py` for Python, `snake_case.html` for templates
- **Exploit docs:** `mcp{ID}_{short_name}.md`
- **Commit messages:** `<type>(<scope>): <description>` (e.g., `feat(mcp-server): add read_file tool`)

---

## Phase Tracker

| Phase | Branch | Description | Status |
|-------|--------|-------------|--------|
| 1 | `phase-1/mcp-foundation` | MCP server/client, file tools, backend, frontend, basic CRUD | **Done** |
| 2 | `phase-2/mcp02-path-traversal` | MCP02 vulnerability, document viewer integration, exploit docs | **Done** |
| 3 | `phase-3/mcp01-secret-exposure` | MCP01 vulnerability, secrets file, exploit docs | **Done** |
| 4 | `phase-4/mcp06-prompt-injection` | MCP06 vulnerability, Ollama integration, exploit docs | **Done** |

## Running

```bash
# Install dependencies
uv sync

# Run the backend (includes MCP server lifecycle)
uv run uvicorn backend.main:app --reload --port 8005

# Run MCP server standalone (for testing)
uv run python -m mcp_server.server

# MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m mcp_server.server

# Lint
uv run ruff check .
```
