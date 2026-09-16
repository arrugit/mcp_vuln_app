"""
VULNEX Backend — FastAPI application entry point.

Responsibilities:
- Create FastAPI app instance
- Mount static files and Jinja2 templates
- Include API routers for documents, tasks, calendar
- Initialize SQLite database on startup
- Seed default user
- Spawn MCP server subprocess on startup
- Shut down MCP server on shutdown
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.database import engine
from backend.mcp_client import mcp_client
from backend.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    On startup:
    - Create database tables if they don't exist
    - Seed default user
    - Spawn the MCP server subprocess

    On shutdown:
    - Stop the MCP server subprocess
    """
    # Startup: initialize database
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default user if none exists
    from sqlalchemy import select

    from backend.database import async_session_factory
    from backend.models import User
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.id == 1))
        if result.scalar_one_or_none() is None:
            default_user = User(
                username="admin",
                email="admin@vulnex.local",
                display_name="Admin User",
            )
            session.add(default_user)
            await session.commit()
            logger.info("Seeded default user (id=1)")

    # Startup: spawn MCP server
    logger.info("Starting MCP server subprocess...")
    await mcp_client.start()

    yield

    # Shutdown: stop MCP server
    logger.info("Stopping MCP server subprocess...")
    await mcp_client.stop()


# Create the FastAPI application
app = FastAPI(
    title="VULNEX",
    description="AI-powered productivity assistant with embedded MCP security vulnerabilities",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files directory
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)

# Include API routers
from backend.routers import calendar, documents, secrets, tasks  # noqa: E402

app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(secrets.router, prefix="/api/secrets", tags=["secrets"])


# Page routes — serve Jinja2 templates
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import RedirectResponse  # noqa: E402

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Redirect root to documents page."""
    return RedirectResponse(url="/documents")


@app.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request) -> HTMLResponse:
    """Render the documents management page."""
    return templates.TemplateResponse("documents.html", {"request": request})


@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request) -> HTMLResponse:
    """Render the task management page."""
    return templates.TemplateResponse("tasks.html", {"request": request})


@app.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request) -> HTMLResponse:
    """Render the calendar page."""
    return templates.TemplateResponse("calendar.html", {"request": request})


@app.get("/secrets", response_class=HTMLResponse)
async def secrets_page(request: Request) -> HTMLResponse:
    """Render the application configuration / secrets page."""
    return templates.TemplateResponse("secrets.html", {"request": request})
