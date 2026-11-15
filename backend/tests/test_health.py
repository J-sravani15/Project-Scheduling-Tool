import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "documentation" in data
    assert "health" in data


@pytest.mark.asyncio
async def test_ping_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Student Project Scheduling Tool"
    assert data["version"] == "1.0.0"
    assert data["environment"] == "development"
    assert "database" in data
    assert "connected" in data["database"]
    assert "database" in data["database"]
    assert "server" in data["database"]
    assert "message" in data["database"]


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = await client.options("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
