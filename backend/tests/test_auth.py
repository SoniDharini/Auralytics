import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_flow(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "test@glownaturals.com",
        "password": "strongPassword123",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@glownaturals.com"
    assert data["user"]["full_name"] == "Test User"
    assert "password_hash" not in data["user"]
    assert "influenceos_refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_duplicate_registration_rejected(client: AsyncClient):
    payload = {
        "full_name": "Test User",
        "email": "duplicate@glownaturals.com",
        "password": "strongPassword123",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_flow_and_me(client: AsyncClient):
    # Register first
    reg_payload = {
        "full_name": "Aaditya Sharma",
        "email": "aaditya.login@glownaturals.com",
        "password": "securePassword456",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Login with valid password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "aaditya.login@glownaturals.com", "password": "securePassword456"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Access /auth/me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "aaditya.login@glownaturals.com"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    reg_payload = {
        "full_name": "Aaditya Sharma",
        "email": "invalid.pass@glownaturals.com",
        "password": "securePassword456",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "invalid.pass@glownaturals.com", "password": "wrongPassword"},
    )
    assert login_res.status_code == 401
    assert "Invalid email or password" in login_res.json()["detail"]


@pytest.mark.asyncio
async def test_session_refresh_and_logout(client: AsyncClient):
    reg_payload = {
        "full_name": "Refresh User",
        "email": "refresh@glownaturals.com",
        "password": "securePassword456",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # Call refresh endpoint using cookie received
    refresh_res = await client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    new_token = refresh_res.json()["access_token"]
    assert new_token is not None

    # Call logout
    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200

    # Refresh after logout should fail
    fail_refresh = await client.post("/api/v1/auth/refresh")
    assert fail_refresh.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_protected_route(client: AsyncClient):
    res = await client.get("/api/v1/campaigns")
    assert res.status_code == 401
