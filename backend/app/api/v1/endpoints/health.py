from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any
from app.core.config import settings
from app.core.database import check_db_connection

router = APIRouter()


class DatabaseStatus(BaseModel):
    connected: bool
    database: str
    server: str
    message: str
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    environment: str
    database: DatabaseStatus


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Returns system health status and PostgreSQL database connection diagnostics.
    """
    db_status = await check_db_connection()
    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        database=DatabaseStatus(**db_status),
    )


@router.get("/ping")
async def ping():
    """Fast liveness check endpoint without DB overhead."""
    return {"ping": "pong"}
