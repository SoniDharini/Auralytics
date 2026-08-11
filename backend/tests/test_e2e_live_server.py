import httpx
import pytest

BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"


@pytest.mark.asyncio
async def test_live_health():
    async with httpx.AsyncClient() as client:
        res = await client.get(HEALTH_URL)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["project"] == "InfluenceOS API"


@pytest.mark.asyncio
async def test_live_seeded_login_flow():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Login with seeded user
        login_res = await client.post(
            "/auth/login",
            json={"email": "aaditya@glownaturals.com", "password": "password123"},
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        assert login_data["user"]["email"] == "aaditya@glownaturals.com"
        assert login_data["user"]["full_name"] == "Aaditya Sharma"
        assert "influenceos_refresh_token" in login_res.cookies
        token = login_data["access_token"]

        # 2. Get /auth/me
        me_res = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "aaditya@glownaturals.com"

        # 3. Test refresh rotation
        refresh_res = await client.post("/auth/refresh", cookies=login_res.cookies)
        assert refresh_res.status_code == 200
        new_token = refresh_res.json()["access_token"]
        assert new_token is not None

        # 4. Logout
        logout_res = await client.post("/auth/logout", cookies=refresh_res.cookies)
        assert logout_res.status_code == 200

        # 5. Refresh with revoked session should fail
        revoked_refresh = await client.post("/auth/refresh", cookies=refresh_res.cookies)
        assert revoked_refresh.status_code == 401


@pytest.mark.asyncio
async def test_live_registration_and_campaign_crud():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        email = f"live.user.{httpx._utils.get_environment_proxies()}@test.com"
        # Unique email
        import uuid
        test_email = f"user.{uuid.uuid4().hex[:6]}@glownaturals.com"

        # 1. Register new user
        reg_payload = {
            "full_name": "Priya Live",
            "email": test_email,
            "password": "SecurePassword123!",
            "company_name": "GlowNaturals Live",
            "role": "brand_manager",
        }
        reg_res = await client.post("/auth/register", json=reg_payload)
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert reg_data["user"]["email"] == test_email
        token = reg_data["access_token"]

        # 2. Duplicate registration rejected
        dup_res = await client.post("/auth/register", json=reg_payload)
        assert dup_res.status_code == 409

        # 3. Create Campaign
        headers = {"Authorization": f"Bearer {token}"}
        camp_payload = {
            "name": "Live Campaign E2E",
            "brand": "GlowNaturals",
            "budget": 300000,
            "objective": "Product Launch",
            "start_date": "2026-10-01",
            "end_date": "2026-11-15",
            "status": "active",
            "health": "excellent",
        }
        camp_res = await client.post("/campaigns", json=camp_payload, headers=headers)
        assert camp_res.status_code == 201
        camp_id = camp_res.json()["id"]

        # 4. List Campaigns
        list_res = await client.get("/campaigns", headers=headers)
        assert list_res.status_code == 200
        camp_ids = [c["id"] for c in list_res.json()]
        assert camp_id in camp_ids

        # 5. List Influencers
        inf_res = await client.get("/influencers", headers=headers)
        assert inf_res.status_code == 200
        assert len(inf_res.json()) >= 1

        # 6. List Approvals
        appr_res = await client.get("/approvals", headers=headers)
        assert appr_res.status_code == 200
        assert len(appr_res.json()) >= 1

        # 7. List Agents
        agents_res = await client.get("/agents", headers=headers)
        assert agents_res.status_code == 200
        assert len(agents_res.json()) >= 1

        # 8. Get Analytics
        analytics_res = await client.get("/analytics", headers=headers)
        assert analytics_res.status_code == 200
        assert len(analytics_res.json()["metrics"]) >= 1
