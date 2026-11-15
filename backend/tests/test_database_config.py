import pytest
from app.core.config import Settings
from app.core.database import Base, check_db_connection


def test_settings_database_url_generation():
    test_settings = Settings(
        POSTGRES_SERVER="db.example.com",
        POSTGRES_PORT=5432,
        POSTGRES_USER="project_user",
        POSTGRES_PASSWORD="secure_password_123",
        POSTGRES_DB="academic_projects",
    )
    
    assert (
        test_settings.async_database_url
        == "postgresql+asyncpg://project_user:secure_password_123@db.example.com:5432/academic_projects"
    )
    assert (
        test_settings.sync_database_url
        == "postgresql+psycopg://project_user:secure_password_123@db.example.com:5432/academic_projects"
    )


def test_settings_database_url_without_password():
    test_settings = Settings(
        POSTGRES_SERVER="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_USER="postgres",
        POSTGRES_PASSWORD="",
        POSTGRES_DB="test_db",
    )
    assert test_settings.async_database_url == "postgresql+asyncpg://postgres@localhost:5432/test_db"


def test_cors_origins_parsing():
    test_settings = Settings(
        BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    assert "http://localhost:5173" in test_settings.BACKEND_CORS_ORIGINS
    assert "http://127.0.0.1:5173" in test_settings.BACKEND_CORS_ORIGINS


def test_base_metadata_registered():
    assert hasattr(Base, "metadata")
    assert Base.metadata is not None


@pytest.mark.asyncio
async def test_check_db_connection_diagnostic_format():
    result = await check_db_connection()
    assert isinstance(result, dict)
    assert "connected" in result
    assert "database" in result
    assert "server" in result
    assert "message" in result
    # Result is a boolean, reporting True or False depending on local DB state
    assert isinstance(result["connected"], bool)
