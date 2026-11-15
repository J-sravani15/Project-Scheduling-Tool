import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models.user import User


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client: AsyncClient, db_session: AsyncSession):
    unique_email = f"student_{uuid.uuid4().hex[:8]}@college.edu"
    password = "StrongPassword2026!"

    # 1. Register student
    reg_payload = {
        "full_name": "Test Student",
        "email": unique_email,
        "password": password,
        "role": "student",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["email"] == unique_email.lower()
    assert user_data["role"] == "student"
    assert "password" not in user_data
    assert "password_hash" not in user_data
    user_id = user_data["id"]

    try:
        # 2. Duplicate registration rejected
        dup_resp = await client.post("/api/v1/auth/register", json=reg_payload)
        assert dup_resp.status_code == 400
        assert "already exists" in dup_resp.json()["detail"].lower()

        # 3. Login with wrong password rejected
        bad_login = await client.post(
            "/api/v1/auth/login/json",
            json={"email": unique_email, "password": "WrongPassword!"},
        )
        assert bad_login.status_code == 401

        # 4. Login with correct password returns JWT token
        good_login = await client.post(
            "/api/v1/auth/login/json",
            json={"email": unique_email, "password": password},
        )
        assert good_login.status_code == 200
        token_data = good_login.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]

        # 5. Access /me with token
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["id"] == user_id

        # 6. Access /me without token rejected
        unauth_resp = await client.get("/api/v1/auth/me")
        assert unauth_resp.status_code == 401

    finally:
        await db_session.execute(delete(User).where(User.email == unique_email.lower()))
        await db_session.commit()
