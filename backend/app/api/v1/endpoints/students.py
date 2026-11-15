from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.user import UserSummary

router = APIRouter()


@router.get("", response_model=List[UserSummary], summary="List registered student accounts")
async def list_students(
    search: Optional[str] = Query(None, description="Optional search by name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lists registered active student accounts with safe profile fields (ID, name, email, role).
    Excludes faculty and inactive accounts. Accessible to authenticated users.
    """
    conditions = [
        User.role == UserRole.STUDENT,
        User.is_active.is_(True),
    ]

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        conditions.append(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
            )
        )

    query = (
        select(User)
        .where(*conditions)
        .order_by(User.full_name.asc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    return list(result.scalars().all())
