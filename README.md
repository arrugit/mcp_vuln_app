# VULNEX

An intentionally vulnerable AI-powered productivity assistant built for academic research on MCP (Model Context Protocol) application security. VULNEX reproduces three real-world vulnerability patterns in a realistic, production-grade web application.

## What is this?

VULNEX is a document management, task tracking, and calendar/scheduling app that looks and functions like a legitimate SaaS product. Under the hood it runs a genuine MCP client/server architecture: the backend is an MCP client only; a separate MCP server process holds all file/document logic. Three security vulnerabilities are embedded in the app, each reproducing a real-world AI/MCP bug pattern.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js + npm (for MCP Inspector, optional)

> Ollama with `llama3.2:3b` will be needed starting Phase 4 (AI summarization). Not required yet.

## Setup

```bash
# Clone the repository
git clone https://github.com/arrugit/mcp_vuln_app.git
cd mcp_vuln_app

# Checkout the latest phase branch
git checkout phase-1/mcp-foundation

# Install dependencies
uv sync
```

No environment files are needed for Phase 1. The app runs with sensible defaults.

## Running

### Start the MCP server (standalone test)

```bash
uv run python -m mcp_server.server
```

This starts the MCP server on stdio transport. It will wait for JSON-RPC input.

### Verify with MCP Inspector

```bash
npx @modelcontextprotocol/inspector uv run python -m mcp_server.server
```

Opens the MCP Inspector UI where you can call `read_file`, `write_file`, `list_files`, and `search_documents` tools interactively.

### Start the backend

```bash
uv run uvicorn backend.main:app --reload --port 8005
```

### Open the UI

Navigate to **http://localhost:8005** in your browser.

## Current Status

### What's live (Phase 1)

- **Document Management** — upload (TXT, MD, PDF, DOCX), list, view content, delete. Content is read via the MCP server's `read_file` tool.
- **Task Management** — create tasks (title, description, priority, due date), kanban board (To Do / In Progress / Review / Done), status updates, comments.
- **Calendar** — monthly grid view, event creation, tasks with due dates appear on the calendar.
- **MCP Architecture** — real MCP client/server wiring. The backend spawns the MCP server as a subprocess and communicates via JSON-RPC over stdio using `ClientSession.call_tool()`. Every file read goes through this protocol path.
- **Frontend** — HTMX + Alpine.js + Jinja2 templates, no build step, professional SaaS aesthetic.

### What's NOT yet exposed

No vulnerability is reachable through the UI in Phase 1. The following starts in subsequent phases:

| Phase | What gets added |
|-------|----------------|
| Phase 2 | MCP02 — Path traversal via blacklist bypass (document viewer exposes `is_path_safe()` bypass) |
| Phase 3 | MCP01 — Secret file exposure (`data/config/secrets.env` accessible via `read_file`) |
| Phase 4 | MCP06 — Indirect prompt injection (Ollama summarization flow processes untrusted document content) |

Exploit documentation will be added to the `exploits/` directory as each phase completes.

## Project Structure

```
vulnex/
  backend/
    main.py              # FastAPI app entrypoint
    mcp_client.py        # MCP client (subprocess + ClientSession)
    models.py            # SQLAlchemy models (User, Document, Task, Event)
    schemas.py           # Pydantic request/response schemas
    database.py          # SQLAlchemy async engine + session factory
    routers/
      documents.py       # Document CRUD + content viewing
      tasks.py           # Task CRUD + kanban status
      calendar.py        # Calendar event CRUD
    services/
      document_service.py  # Document business logic
      task_service.py      # Task business logic
      mcp_service.py       # High-level MCP tool call wrappers
    templates/             # Jinja2 templates (HTMX + Alpine.js)
    static/css/style.css   # Global styles
  mcp_server/
    server.py            # MCPServer (v2) with stdio transport
    file_tools.py        # read_file, write_file, list_files, search_documents
    __main__.py          # Entry point for `python -m mcp_server`
  data/
    uploads/             # User-uploaded documents
    config/              # Application config (secrets.env added in Phase 3)
    vulnex.db            # SQLite database (created at runtime)
  exploits/              # Exploit documentation (added per phase)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Package manager | uv |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Frontend | HTMX 1.9 + Alpine.js 3.x + Jinja2 |
| MCP SDK | `mcp` Python package (v2, `MCPServer`) |
| MCP Transport | stdio |
| LLM (Phase 4) | Local Ollama, `llama3.2:3b` |
| Port | 8005 |

## Development

```bash
# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check . --fix
```

## License

University final-year project — not for production use.
