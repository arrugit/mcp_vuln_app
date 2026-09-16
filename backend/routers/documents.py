"""
Document Router — API endpoints for document management.

Handles document listing, viewing (via MCP read_file), uploading,
searching, and deletion. Summarization endpoint will be added in Phase 4.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import DocumentContent, DocumentResponse
from backend.services import document_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Upload directory
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """
    List all documents, optionally filtered by folder.

    Returns documents owned by the default user (id=1) for this
    single-user application.
    """
    docs = await document_service.list_documents(db, owner_id=1, folder_id=folder_id)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get document metadata by ID."""
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}/content", response_model=DocumentContent)
async def get_document_content(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
) -> DocumentContent:
    """
    Get document content for viewing.

    Reads the file via the MCP server's read_file tool and returns
    the text content. This is the primary entry point for MCP02
    (path traversal) when combined with crafted paths.
    """
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        content = await document_service.get_document_content(doc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return DocumentContent(id=doc.id, filename=doc.filename, content=content)


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Upload a new document.

    Saves the file to data/uploads/ and creates a database record.
    Supports PDF, TXT, MD, and DOCX formats.
    """
    # Validate file type
    allowed_types = {".txt", ".md", ".pdf", ".docx"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{suffix}' not supported. Allowed: {allowed_types}",
        )

    # Save file to disk
    file_content = await file.read()
    # Use a safe filename to avoid path issues
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    save_path = UPLOAD_DIR / safe_filename

    # Avoid overwriting existing files
    counter = 1
    while save_path.exists():
        stem = Path(file.filename).stem
        save_path = UPLOAD_DIR / f"{stem}_{counter}{suffix}"
        counter += 1

    save_path.write_bytes(file_content)

    # Create database record
    doc = await document_service.create_document(
        db=db,
        filename=file.filename,
        filepath=save_path.name,
        mime_type=file.content_type,
        size_bytes=len(file_content),
        folder_id=folder_id,
        owner_id=1,
    )

    return DocumentResponse.model_validate(doc)


@router.get("/search/", response_model=list[DocumentResponse])
async def search_documents(
    q: str = "",
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """
    Search documents by filename or content.

    Uses the MCP server's search_documents tool for content search.
    """
    if not q:
        return []

    # First search via MCP
    from backend.services import mcp_service
    results = await mcp_service.search_documents(q)

    # Map results back to document IDs
    docs = []
    for result in results:
        filepath = result.get("path", "")
        filename = Path(filepath).name
        doc_list = await document_service.list_documents(db, owner_id=1)
        for d in doc_list:
            if d.filename == filename:
                docs.append(d)
                break

    return [DocumentResponse.model_validate(d) for d in docs]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a document by ID."""
    deleted = await document_service.delete_document(db, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}


@router.post("/{doc_id}/summarize")
async def summarize_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Summarize a document using AI.

    Placeholder — full implementation with Ollama will be added in Phase 4.
    For now, returns a basic extractive summary.
    """
    doc = await document_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        content = await document_service.get_document_content(doc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Simple extractive summary (first 500 chars)
    summary = content[:500] + "..." if len(content) > 500 else content

    return {"id": doc.id, "filename": doc.filename, "summary": summary}
