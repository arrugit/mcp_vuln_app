# VULNEX — Product Requirements Document (PRD)

> **Version:** 1.0  
> **Status:** Draft for Review  
> **Date:** 2026-09-12  
> **Purpose:** University final-year project on AI/MCP application security testing

---

## 1. Executive Summary

VULNEX is a **production-grade AI-powered productivity assistant** delivered as a SaaS-style web application. It provides document management, task tracking, and calendar/scheduling capabilities. The application appears and functions as a legitimate, polished productivity tool.

Under the hood, VULNEX is built on a genuine **Model Context Protocol (MCP)** client/server architecture. The backend acts as an MCP client that communicates with a standalone MCP server over stdio JSON-RPC. This architecture is authentic, not a monolith with MCP-flavored naming.

**The core purpose of this project is security research.** VULNEX contains three intentionally embedded vulnerabilities that reproduce real-world AI/MCP security bug patterns. These vulnerabilities are realistic, well-documented, and discoverable through standard security testing. The application surface reveals nothing about its vulnerable-by-design nature.

---

## 2. Target Users

| Persona | Role | Context |
|---------|------|---------|
| **Security Researcher** | Primary evaluator | Tests the application for vulnerabilities; uses exploit documentation to verify findings |
| **University Assessor** | Project evaluator | Reviews architecture, code quality, documentation, and exploit guides |
| **End User (simulated)** | Productivity worker | Uses VULNEX as a normal productivity tool; triggers vulnerabilities indirectly through normal usage |

---

## 3. Core Product Features

### 3.1 Document Management

**User Story:** As a user, I want to upload, view, organize, and get AI-powered summaries of my documents so I can stay productive.

| Feature | Description |
|---------|-------------|
| **Upload Documents** | Drag-and-drop or file picker upload; supports PDF, TXT, MD, DOCX; stored in app data directory |
| **Document Viewer** | In-browser rendering of uploaded documents; supports markdown preview |
| **AI Summarization** | User requests a summary of a document; backend calls the MCP server's `summarize_document` tool which reads and summarizes content |
| **Document Organization** | Create folders, move documents between folders; flat folder tree |
| **Document Search** | Full-text search across uploaded documents |

### 3.2 Task Management

**User Story:** As a user, I want to create, assign, and track tasks with due dates and priorities so I can manage my work.

| Feature | Description |
|---------|-------------|
| **Create Tasks** | Title, description, priority (low/medium/high/urgent), due date, assignee |
| **Task Board** | Kanban-style view: To Do → In Progress → Review → Done |
| **Task Assignment** | Assign tasks to team members (simulated with local users) |
| **Task Filtering** | Filter by priority, assignee, due date range, status |
| **Task Comments** | Add comments/notes to tasks |

### 3.3 Calendar & Scheduling

**User Story:** As a user, I want a calendar view of my tasks and events so I can plan my time.

| Feature | Description |
|---------|-------------|
| **Monthly Calendar View** | Standard month grid showing tasks with due dates |
| **Event Creation** | Create one-time or recurring events |
| **Integration with Tasks** | Tasks with due dates auto-appear on calendar |
| **Today/Week Navigation** | Quick navigation to current day, week view |

---

## 4. Technical Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (HTMX + Alpine.js + Jinja2 Templates)        │
│  Served by FastAPI on port 8005                         │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy + SQLite)                 │
│  - Application logic, auth, CRUD                        │
│  - Acts as MCP CLIENT only                              │
│  - Spawns MCP server as subprocess (stdio transport)    │
└────────────────────────┬────────────────────────────────┘
                         │ JSON-RPC over stdio (MCP protocol)
┌────────────────────────▼────────────────────────────────┐
│  MCP Server (mcp Python SDK, FastMCP)                   │
│  - Standalone process                                   │
│  - Exposes tools via @mcp.tool()                        │
│  - Handles file operations, document reading            │
│  - Contains all vulnerability logic                      │
└─────────────────────────────────────────────────────────┘
```

**Key Constraint:** The backend **never** imports MCP server functions directly. Every interaction with file/document/vulnerable logic goes through a real MCP protocol call via `ClientSession.call_tool()`. The summarization flow lives entirely on the backend side: the backend reads document content via MCP `read_file`, sends it to the local Ollama model, and executes whatever tool call the model returns via MCP.

---

## 5. Vulnerability Features (Product Requirements)

The following features exist in VULNEX. From a product perspective, they are legitimate features with subtle design flaws. Each flaw is documented in the TDD and exploit documentation.

### 5.1 Feature: Secure Document Viewing

**Product Description:** When a user requests to view or summarize a document, the system performs a path-safety check to ensure the requested file is within the allowed documents directory. The system blocks access to sensitive system directories (e.g., `/etc`, `~/.ssh`) to prevent unauthorized file access.

**Known Limitation (MCP02):** The path-safety check uses exact string matching against a blacklist of directory names. It does not resolve symlinks, canonicalize paths, or check if a path is a subdirectory of a blocked location. A path like `/etc/shadow` or `~/.ssh/../.ssh/id_rsa` is not caught because the literal string does not match the blacklist entry exactly.

### 5.2 Feature: Application Secrets Management

**Product Description:** VULNEX stores its configuration and third-party API keys in a local configuration file (`config/secrets.env`) that the application reads at startup. This file contains realistic-looking credentials needed for integrations (email, calendar sync, AI provider keys).

**Known Limitation (MCP01):** The secrets file resides on the local filesystem in a location accessible to the MCP server's file-reading tools. The path-safety check from Feature 5.1 does not protect this file because the secrets directory is not in the hardcoded blacklist. An attacker who can bypass the path check (via MCP02) can read the secrets file.

### 5.3 Feature: AI-Powered Document Summarization

**Product Description:** Users can request an AI-generated summary of any uploaded document. The backend reads the document content via the MCP server's `read_file` tool, then sends the content to a local Ollama model (llama3.2:3b, configurable) for summarization. The Ollama model is presented with the document content and the available MCP tool schema; the model's response determines which MCP tool gets called next (if any) and with what arguments. The backend then executes that tool call via `ClientSession.call_tool(...)`.

**Known Limitation (MCP06):** The Ollama model processes the raw document content when deciding its next action. A malicious document can contain hidden natural-language instructions (e.g., in a comment block, invisible text, or embedded directive) that redirect the AI agent to invoke the `read_file` tool on a different, sensitive path (e.g., the secrets file from Feature 5.2) rather than or in addition to summarizing the user's document. Because the instruction is embedded in the data the model reads, the model treats it as a directive — this is the indirect prompt injection vector.

---

## 6. Vulnerability Summary Table

| ID | Name | Phase | Bug Category | Hides Inside | Chain |
|----|------|-------|--------------|--------------|-------|
| **MCP02** | Privilege Escalation via Scope Creep | 2 | Path traversal / blacklist bypass | Secure Document Viewing | Standalone; enables MCP01 |
| **MCP01** | Token Mismanagement & Secret Exposure | 3 | Secret file reachable via MCP tool | Application Secrets Management | Chained from MCP02 |
| **MCP06** | Intent Flow Subversion | 4 | Indirect prompt injection | AI Document Summarization | Chains with MCP01 via MCP02 |

---

## 7. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| **Port** | 8005 (backend + frontend) |
| **Database** | SQLite via SQLAlchemy; file: `data/vulnex.db` |
| **Package Manager** | `uv` only; no Docker, no pip, no poetry |
| **Python Version** | 3.11+ |
| **Frontend** | HTMX 1.9+, Alpine.js 3.x, Jinja2 templates; no build step |
| **UI Style** | Clean, calm, professional SaaS aesthetic; muted color palette; no harsh gradients |
| **MCP SDK** | Official `mcp` Python package; `FastMCP` class for server; `ClientSession` for client |
| **MCP Transport** | stdio only (server spawned as subprocess by backend) |
| **MCP Server Standalone** | Server must be independently launchable and callable via MCP Inspector CLI |
| **LLM Runtime** | Local Ollama instance; model: `llama3.2:3b` (configurable via env var `VULNEX_OLLAMA_MODEL`); called from backend (MCP client side) |
| **Code Comments** | All functions heavily commented; assume reader needs full context |
| **Documentation** | CLAUDE.md maintained throughout; exploit docs per vulnerability |

---

## 8. UI/Design Requirements

### 8.1 Color Palette

| Element | Color | Purpose |
|---------|-------|---------|
| Primary | `#4A6FA5` (muted blue) | Headers, buttons, active states |
| Secondary | `#7B8794` (warm gray) | Text, borders, secondary actions |
| Background | `#F8F9FA` (off-white) | Page background |
| Surface | `#FFFFFF` | Cards, modals, inputs |
| Accent | `#6B9E78` (muted green) | Success states, completed tasks |
| Warning | `#D4A574` (muted amber) | Urgent priorities, alerts |
| Error | `#C25B56` (muted red) | Error states, high-priority items |

### 8.2 Layout

- **Navigation:** Left sidebar with icon + label for Documents, Tasks, Calendar
- **Content Area:** Right panel with header, filters, and content cards
- **Modals:** For task creation, document upload, event creation
- **Responsive:** Must work at 1024px+ width; no mobile requirement

### 8.3 Interaction Patterns

- HTMX for server-driven partial page updates (no full reloads)
- Alpine.js for client-side interactivity (modals, dropdowns, drag-and-drop on task board)
- Smooth transitions on card moves and state changes

---

## 9. File Structure (Target)

```
vulnex/
├── CLAUDE.md                    # Architecture & conventions reference
├── PRD.md                       # This document
├── TDD.md                       # Technical Design Document
├── .gitattributes
├── pyproject.toml               # uv project config
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── mcp_client.py            # MCP client (subprocess spawn + ClientSession)
│   ├── llm_client.py            # Ollama integration (summarization flow)
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── routers/
│   │   ├── documents.py         # Document CRUD + summarization endpoints
│   │   ├── tasks.py             # Task CRUD endpoints
│   │   └── calendar.py          # Calendar endpoints
│   ├── services/
│   │   ├── document_service.py  # Document business logic
│   │   ├── task_service.py      # Task business logic
│   │   ├── mcp_service.py       # High-level MCP call wrappers
│   │   └── summarization_service.py  # Ollama + MCP tool-call orchestration
│   └── templates/               # Jinja2 templates
│       ├── base.html
│       ├── documents.html
│       ├── tasks.html
│       └── calendar.html
├── mcp_server/
│   ├── __init__.py              # Package marker
│   ├── server.py                # FastMCP server with @mcp.tool() definitions
│   ├── file_tools.py            # File reading/writing tools (vulnerable logic)
│   └── __main__.py              # Entry point for `python -m mcp_server`
├── data/                        # Runtime data
│   ├── vulnex.db                # SQLite database
│   ├── uploads/                 # User-uploaded documents
│   └── config/
│       └── secrets.env          # Application secrets (fake API keys)
└── exploits/                    # Exploit documentation
    ├── mcp02_path_traversal.md
    ├── mcp01_secret_exposure.md
    └── mcp06_prompt_injection.md
```

---

## 10. Success Criteria

1. **Functional App:** VULNEX runs on port 8005, serves a polished UI, and all productivity features work end-to-end
2. **Genuine MCP Architecture:** MCP server is independently testable via MCP Inspector; backend never imports server functions directly
3. **Vulnerability Fidelity:** Each vulnerability reproduces the same real-world bug pattern it documents (CVE lineage)
4. **Discoverability:** Each vulnerability can be found through standard security testing without reading exploit docs
5. **Documentation Completeness:** Each vulnerability has a working exploit guide with step-by-step instructions
6. **Code Quality:** All code is heavily commented and maintainable; CLAUDE.md stays current

---

## 11. Out of Scope

- Real authentication/authorization (use a simulated single-user or simple login)
- Real third-party API integrations (secrets file contains fake keys)
- Deployment, CI/CD, or production readiness
- Mobile responsiveness
- Real-time collaboration

---

## Appendix: CVE Lineage Reference

| Vuln ID | Real-World CVE/Bug Pattern | Source |
|---------|---------------------------|--------|
| MCP02 | Path traversal via blacklist bypass | Zen MCP Server CVE-2025-66689 |
| MCP01 | Secret file exposure via file tool | Common MCP misconfiguration |
| MCP06 | Indirect prompt injection via document content | Emerging AI agent attack vector |
