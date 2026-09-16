"""
Calendar Router — API endpoints for calendar and event management.

Handles event CRUD and calendar data queries. Tasks with due dates
automatically appear on the calendar.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Event, Task
from backend.schemas import EventCreate, EventResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[EventResponse])
async def list_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
) -> list[EventResponse]:
    """
    List events within a date range.

    Defaults to the current month if no dates are provided.
    Also includes tasks with due dates as calendar events.
    """
    now = datetime.utcnow()
    if start_date is None:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if end_date is None:
        # End of the month
        if now.month == 12:
            end_date = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0)
        else:
            end_date = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0)

    # Fetch explicit events
    query = select(Event).where(
        and_(Event.start_time >= start_date, Event.start_time <= end_date)
    )
    result = await db.execute(query)
    events = list(result.scalars().all())

    # Also fetch tasks with due dates in the range
    task_query = select(Task).where(
        and_(Task.due_date >= start_date, Task.due_date <= end_date)
    )
    task_result = await db.execute(task_query)
    tasks = list(task_result.scalars().all())

    # Convert tasks to event-like responses
    responses = [EventResponse.model_validate(e) for e in events]
    for task in tasks:
        responses.append(
            EventResponse(
                id=task.id + 10000,  # Offset to avoid ID collision
                title=task.title,
                description=task.description,
                start_time=task.due_date,
                end_time=task.due_date + timedelta(hours=1),
                is_recurring=False,
                recurrence=None,
                task_id=task.id,
                created_at=task.created_at,
            )
        )

    return responses


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """Get an event by ID."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event)


@router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    """Create a new calendar event."""
    event = Event(
        title=event_data.title,
        description=event_data.description,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        is_recurring=event_data.is_recurring,
        recurrence=event_data.recurrence,
        task_id=event_data.task_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    logger.info("Created event: %s (id=%d)", event.title, event.id)
    return EventResponse.model_validate(event)


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a calendar event."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    logger.info("Deleted event id=%d", event_id)
    return {"success": True}
