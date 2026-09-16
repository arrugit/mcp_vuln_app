"""
Database Configuration — SQLAlchemy async engine and session factory.

Uses aiosqlite for async SQLite access. The database file is located
at data/vulnex.db relative to the project root.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Database file path — relative to project root
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "vulnex.db"

# Ensure the data directory exists
DB_DIR.mkdir(parents=True, exist_ok=True)

# Async SQLite engine
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory — each request gets its own session
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session.

    Used with FastAPI's Depends() to inject a session into route handlers.
    The session is automatically closed after the request completes.

    Yields:
        AsyncSession: A SQLAlchemy async session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
