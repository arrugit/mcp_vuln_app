"""
Pydantic Schemas — Request/response models for the VULNEX API.

These schemas validate incoming requests and structure outgoing responses.
They mirror the SQLAlchemy models but are decoupled from the database layer.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# --- Document Schemas ---

class DocumentCreate(BaseModel):
    """Schema for creating a new document (via upload)."""
    filename: str
    folder_id: Optional[int] = None


class DocumentResponse(BaseModel):
    """Schema for returning document metadata."""
    id: int
    filename: str
    filepath: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    folder_id: Optional[int] = None
    owner_id: int
    summary: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentContent(BaseModel):
    """Schema for returning document content for viewing."""
    id: int
    filename: str
    content: str


class DocumentSummary(BaseModel):
    """Schema for returning an AI-generated summary."""
    id: int
    filename: str
    summary: str


# --- Task Schemas ---

class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|review|done)$")
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskResponse(BaseModel):
    """Schema for returning task data."""
    id: int
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    assignee_id: Optional[int] = None
    assignee_name: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskCommentCreate(BaseModel):
    """Schema for adding a comment to a task."""
    content: str = Field(..., min_length=1)
    author_id: int


class TaskCommentResponse(BaseModel):
    """Schema for returning a task comment."""
    id: int
    task_id: int
    author_id: int
    author_name: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Event Schemas ---

class EventCreate(BaseModel):
    """Schema for creating a calendar event."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurrence: Optional[str] = Field(None, pattern="^(daily|weekly|monthly)$")
    task_id: Optional[int] = None


class EventResponse(BaseModel):
    """Schema for returning calendar event data."""
    id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool
    recurrence: Optional[str] = None
    task_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- User Schemas ---

class UserResponse(BaseModel):
    """Schema for returning user data."""
    id: int
    username: str
    email: str
    display_name: str

    class Config:
        from_attributes = True


# --- Generic ---

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    detail: Optional[str] = None
