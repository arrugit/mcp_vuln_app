"""
Document Service — Business logic for document operations.

Handles document CRUD, file storage, and retrieval. All file operations
go through the MCP service (which calls the MCP server via protocol).
"""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Document
from backend.services import mcp_service

logger = logging.getLogger(__name__)

# Upload directory — relative to project root
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def create_document(
    db: AsyncSession,
    filename: str,
    filepath: str,
    mime_type: Optional[str] = None,
    size_bytes: Optional[int] = None,
    folder_id: Optional[int] = None,
    owner_id: int = 1,
) -> Document:
    """
    Create a new document record in the database.

    Args:
        db: Database session.
        filename: Original upload filename.
        filepath: Relative path in the uploads directory.
        mime_type: MIME type of the file.
        size_bytes: File size in bytes.
        folder_id: Parent folder ID (None for root).
        owner_id: ID of the owning user.

    Returns:
        The created Document instance.
    """
    doc = Document(
        filename=filename,
        filepath=filepath,
        mime_type=mime_type,
        size_bytes=size_bytes,
        folder_id=folder_id,
        owner_id=owner_id,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    logger.info("Created document: %s (id=%d)", filename, doc.id)
    return doc


async def get_document(db: AsyncSession, doc_id: int) -> Optional[Document]:
    """
    Retrieve a document by ID.

    Args:
        db: Database session.
        doc_id: Document ID.

    Returns:
        The Document instance, or None if not found.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession,
    owner_id: int = 1,
    folder_id: Optional[int] = None,
) -> list[Document]:
    """
    List all documents for a user, optionally filtered by folder.

    Args:
        db: Database session.
        owner_id: Filter by owner.
        folder_id: Filter by folder (None for root).

    Returns:
        List of Document instances.
    """
    query = select(Document).where(Document.owner_id == owner_id)
    if folder_id is not None:
        query = query.where(Document.folder_id == folder_id)
    else:
        query = query.where(Document.folder_id.is_(None))
    query = query.order_by(Document.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_document_content(doc: Document) -> str:
    """
    Read document content via the MCP server.

    Constructs the full absolute path from the document's relative filepath
    and calls mcp_service.read_file() to retrieve the content.

    Args:
        doc: The Document instance.

    Returns:
        File contents as a string.

    Raises:
        ValueError: If the file cannot be read.
    """
    full_path = str(UPLOAD_DIR / doc.filepath)
    return await mcp_service.read_file(full_path)


async def delete_document(db: AsyncSession, doc_id: int) -> bool:
    """
    Delete a document record and its file.

    Args:
        db: Database session.
        doc_id: Document ID to delete.

    Returns:
        True if deleted, False if not found.
    """
    doc = await get_document(db, doc_id)
    if doc is None:
        return False

    # Delete the file from disk
    file_path = UPLOAD_DIR / doc.filepath
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    logger.info("Deleted document: %s (id=%d)", doc.filename, doc_id)
    return True
