"""
SQLAlchemy Models — Database schema for VULNEX.

Defines the ORM models for:
- User: simulated local users for task assignment
- Document: uploaded files with metadata
- Folder: document organization
- Task: kanban-style task tracking
- Event: calendar events
"""


from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class User(Base):
    """Simulated local user for task assignment."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    documents = relationship("Document", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")
    folders = relationship("Folder", back_populates="owner")


class Folder(Base):
    """Folder for organizing documents."""

    __tablename__ = "folders"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    owner = relationship("User", back_populates="folders")
    documents = relationship("Document", back_populates="folder")


class Document(Base):
    """Uploaded document with metadata and optional AI summary."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    mime_type = Column(String(100))
    size_bytes = Column(Integer)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    owner = relationship("User", back_populates="documents")
    folder = relationship("Folder", back_populates="documents")


class Task(Base):
    """Task with kanban status, priority, and assignment."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    status = Column(String(20), default="todo")  # todo, in_progress, review, done
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    assignee = relationship("User", back_populates="tasks")
    comments = relationship("TaskComment", back_populates="task")
    events = relationship("Event", back_populates="task")


class TaskComment(Base):
    """Comment on a task."""

    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User")


class Event(Base):
    """Calendar event, optionally linked to a task."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence = Column(String(50), nullable=True)  # daily, weekly, monthly
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    task = relationship("Task", back_populates="events")
