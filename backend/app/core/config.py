import json
import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Student Project Scheduling Tool"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            return json.loads(v)
        return v

    # PostgreSQL Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "student_project_scheduler"

    # Authentication & Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-student-scheduling-tool"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"

    @property
    def async_database_url(self) -> str:
        """Constructs the asyncpg PostgreSQL connection URL."""
        if self.POSTGRES_PASSWORD:
            user_auth = f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        else:
            user_auth = self.POSTGRES_USER
        return f"postgresql+asyncpg://{user_auth}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_url(self) -> str:
        """Constructs the synchronous psycopg PostgreSQL connection URL (for Alembic migrations)."""
        if self.POSTGRES_PASSWORD:
            user_auth = f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        else:
            user_auth = self.POSTGRES_USER
        return f"postgresql+psycopg://{user_auth}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend", ".env"),
            "backend/.env",
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
