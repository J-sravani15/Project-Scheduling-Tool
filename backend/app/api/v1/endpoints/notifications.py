from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import (
    ProjectNotificationRead,
    NotificationListResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse, summary="List notifications for the current user")
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists persistent in-app notifications for the authenticated user, ordered newest first.
    Includes unread count and total count.
    """
    items, unread_count, total_count = await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )
    return NotificationListResponse(
        items=items,
        unread_count=unread_count,
        total_count=total_count,
    )


@router.patch("/{notification_id}/read", response_model=ProjectNotificationRead, summary="Mark notification as read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks a specific notification as read.
    Enforces authorization: users can only mark their own notifications.
    """
    notif = await NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied.",
        )
    return notif


@router.post("/mark-all-read", summary="Mark all notifications as read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks all unread notifications for the authenticated user as read.
    """
    count = await NotificationService.mark_all_as_read(
        db=db,
        user_id=current_user.id,
    )
    return {
        "updated_count": count,
        "message": f"{count} notifications marked as read.",
    }


@router.post("/trigger-reminders", summary="Trigger deadline check and academic alerts evaluation")
async def trigger_deadline_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an on-demand evaluation of approaching deadlines, overdue tasks,
    upcoming milestones, and review reminders.
    Safe and idempotent: duplicate notifications for identical intervals are prevented.
    """
    deadline_stats = await NotificationService.check_and_generate_deadline_reminders(db=db)
    academic_stats = await NotificationService.check_and_generate_academic_alerts(db=db)
    return {
        "status": "success",
        "deadline_reminders": deadline_stats,
        "academic_alerts": academic_stats,
    }
