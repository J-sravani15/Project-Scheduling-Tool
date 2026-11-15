from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.project import AcademicProject, ProjectMember
from app.models.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Validates JWT access token if present; returns None if missing or invalid."""
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validates JWT access token and fetches authenticated active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


async def get_current_student(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures authenticated user has STUDENT role."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a student account.",
        )
    return current_user


async def get_current_faculty(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures authenticated user has FACULTY role."""
    if current_user.role != UserRole.FACULTY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires a faculty account.",
        )
    return current_user


async def verify_project_access(
    project_id: UUID,
    current_user: User,
    db: AsyncSession,
    require_owner: bool = False,
    require_write: bool = False,
) -> AcademicProject:
    """
    Validates project existence and RBAC permissions:
    - Owners have full read/write/admin rights.
    - Project members have read/write rights.
    - Assigned faculty guides have read/review rights.
    - Unrelated users receive 403 Forbidden.
    """
    proj_query = await db.execute(
        select(AcademicProject)
        .options(
            selectinload(AcademicProject.members),
            selectinload(AcademicProject.milestones),
        )
        .where(AcademicProject.id == project_id)
    )
    project = proj_query.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    is_owner = (project.owner_id == current_user.id)
    is_faculty_guide = (project.faculty_guide_id == current_user.id)
    is_member = any(m.user_id == current_user.id for m in project.members)

    if require_owner and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires project owner privileges.",
        )

    if require_write and not (is_owner or is_member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access denied for this project.",
        )

    if not (is_owner or is_member or is_faculty_guide):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this project.",
        )

    return project
