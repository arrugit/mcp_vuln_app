"""
Task Service — Business logic for task management operations.

Handles task CRUD, status updates, assignment, and filtering.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import Task, TaskComment

logger = logging.getLogger(__name__)


async def create_task(
    db: AsyncSession,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    assignee_id: Optional[int] = None,
    due_date: Optional[datetime] = None,
) -> Task:
    """
    Create a new task.

    Args:
        db: Database session.
        title: Task title.
        description: Optional task description.
        priority: One of 'low', 'medium', 'high', 'urgent'.
        assignee_id: ID of the assigned user.
        due_date: Optional due date.

    Returns:
        The created Task instance.
    """
    task = Task(
        title=title,
        description=description,
        priority=priority,
        assignee_id=assignee_id,
        due_date=due_date,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    logger.info("Created task: %s (id=%d)", title, task.id)
    return task


async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    """
    Retrieve a task by ID with its assignee and comments loaded.

    Args:
        db: Database session.
        task_id: Task ID.

    Returns:
        The Task instance, or None if not found.
    """
    query = (
        select(Task)
        .options(selectinload(Task.assignee), selectinload(Task.comments))
        .where(Task.id == task_id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[int] = None,
) -> list[Task]:
    """
    List tasks with optional filters.

    Args:
        db: Database session.
        status: Filter by status (todo, in_progress, review, done).
        priority: Filter by priority (low, medium, high, urgent).
        assignee_id: Filter by assignee.

    Returns:
        List of Task instances.
    """
    query = select(Task).options(selectinload(Task.assignee))
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    query = query.order_by(Task.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_task(
    db: AsyncSession,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[int] = None,
    due_date: Optional[datetime] = None,
) -> Optional[Task]:
    """
    Update a task's fields.

    Only provided (non-None) fields are updated.

    Args:
        db: Database session.
        task_id: Task ID to update.
        title: New title.
        description: New description.
        priority: New priority.
        status: New status.
        assignee_id: New assignee.
        due_date: New due date.

    Returns:
        Updated Task instance, or None if not found.
    """
    task = await get_task(db, task_id)
    if task is None:
        return None

    if title is not None:
        task.title = title
    if description is not None:
        task.description = description
    if priority is not None:
        task.priority = priority
    if status is not None:
        task.status = status
    if assignee_id is not None:
        task.assignee_id = assignee_id
    if due_date is not None:
        task.due_date = due_date

    task.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(task)
    logger.info("Updated task id=%d", task_id)
    return task


async def add_comment(
    db: AsyncSession,
    task_id: int,
    author_id: int,
    content: str,
) -> TaskComment:
    """
    Add a comment to a task.

    Args:
        db: Database session.
        task_id: Task to comment on.
        author_id: ID of the comment author.
        content: Comment text.

    Returns:
        The created TaskComment instance.
    """
    comment = TaskComment(
        task_id=task_id,
        author_id=author_id,
        content=content,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    logger.info("Added comment to task id=%d by user id=%d", task_id, author_id)
    return comment


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    """
    Delete a task and its comments.

    Args:
        db: Database session.
        task_id: Task ID to delete.

    Returns:
        True if deleted, False if not found.
    """
    task = await get_task(db, task_id)
    if task is None:
        return False
    await db.delete(task)
    logger.info("Deleted task id=%d", task_id)
    return True
