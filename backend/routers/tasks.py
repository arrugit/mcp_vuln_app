"""
Task Router — API endpoints for task management.

Handles task CRUD, kanban status updates, filtering, and comments.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import (
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from backend.services import task_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """
    List tasks with optional filters.

    Supports filtering by status, priority, and assignee.
    Returns all tasks if no filters are provided.
    """
    tasks = await task_service.list_tasks(
        db, status=status, priority=priority, assignee_id=assignee_id
    )
    responses = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        if t.assignee:
            resp.assignee_name = t.assignee.display_name
        responses.append(resp)
    return responses


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get a task by ID with its assignee info."""
    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = TaskResponse.model_validate(task)
    if task.assignee:
        resp.assignee_name = task.assignee.display_name
    return resp


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new task."""
    task = await task_service.create_task(
        db=db,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        assignee_id=task_data.assignee_id,
        due_date=task_data.due_date,
    )
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update a task's fields (partial update)."""
    task = await task_service.update_task(
        db=db,
        task_id=task_id,
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        status=task_data.status,
        assignee_id=task_data.assignee_id,
        due_date=task_data.due_date,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = TaskResponse.model_validate(task)
    if task.assignee:
        resp.assignee_name = task.assignee.display_name
    return resp


@router.post("/{task_id}/status")
async def update_task_status(
    task_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Update a task's kanban status.

    Used by the drag-and-drop task board. Accepts: todo, in_progress, review, done.
    """
    if status not in ("todo", "in_progress", "review", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")

    task = await task_service.update_task(db, task_id=task_id, status=status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
async def add_comment(
    task_id: int,
    comment_data: TaskCommentCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskCommentResponse:
    """Add a comment to a task."""
    task = await task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    comment = await task_service.add_comment(
        db=db,
        task_id=task_id,
        author_id=comment_data.author_id,
        content=comment_data.content,
    )
    return TaskCommentResponse.model_validate(comment)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a task by ID."""
    deleted = await task_service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}
