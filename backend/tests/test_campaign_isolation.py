import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_new_user_starts_with_clean_workspace(client: AsyncClient):
    """Test 1: New user begins with a completely empty workspace and no fake data."""
    reg_payload = {
        "full_name": "New Brand Manager",
        "email": "clean.user@influenceos.ai",
        "password": "cleanPassword123",
        "company_name": "Organic Glow",
        "role": "marketing_manager",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Campaigns must be empty
    camps_res = await client.get("/api/v1/campaigns", headers=headers)
    assert camps_res.status_code == 200
    assert camps_res.json() == []

    # 2. Activities must be empty
    acts_res = await client.get("/api/v1/activities", headers=headers)
    assert acts_res.status_code == 200
    assert acts_res.json() == []

    # 3. Dashboard summary must show 0s
    summary_res = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_campaigns"] == 0
    assert summary["active_campaigns"] == 0
    assert summary["total_spend"] == 0
    assert summary["total_revenue"] == 0
    assert summary["average_roas"] == 0
    assert summary["pending_approvals"] == 0


@pytest.mark.asyncio
async def test_campaign_lifecycle_and_activities(client: AsyncClient):
    """Test 2-5: Create, Read, Update, Delete with real activity timeline."""
    reg_payload = {
        "full_name": "Lifecycle Tester",
        "email": "lifecycle@influenceos.ai",
        "password": "securePassword123",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Campaign
    create_payload = {
        "name": "GlowNaturals Summer Launch",
        "brand": "GlowNaturals",
        "budget": 200000,
        "objective": "Product Launch",
        "start_date": "2026-09-01",
        "end_date": "2026-10-15",
        "status": "active",
        "health": "healthy",
        "platforms": ["instagram", "youtube"],
    }
    create_res = await client.post("/api/v1/campaigns", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    camp = create_res.json()
    camp_id = camp["id"]
    assert camp["name"] == "GlowNaturals Summer Launch"
    assert camp["budget"] == 200000

    # 2. Verify in campaigns list
    list_res = await client.get("/api/v1/campaigns", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Verify activity recorded
    acts_res = await client.get(f"/api/v1/campaigns/{camp_id}/activities", headers=headers)
    assert acts_res.status_code == 200
    acts = acts_res.json()
    assert len(acts) == 1
    assert acts[0]["activity_type"] == "CAMPAIGN_CREATED"

    # 4. Update Campaign (Budget & Status)
    patch_res = await client.patch(
        f"/api/v1/campaigns/{camp_id}",
        json={"budget": 250000, "status": "paused"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated_camp = patch_res.json()
    assert updated_camp["budget"] == 250000
    assert updated_camp["status"] == "paused"

    # 5. Verify update activity
    acts_res2 = await client.get(f"/api/v1/campaigns/{camp_id}/activities", headers=headers)
    assert acts_res2.status_code == 200
    assert len(acts_res2.json()) == 2

    # 6. Delete Campaign
    del_res = await client.delete(f"/api/v1/campaigns/{camp_id}", headers=headers)
    assert del_res.status_code == 204

    # 7. Verify Campaign is gone
    get_res = await client.get(f"/api/v1/campaigns/{camp_id}", headers=headers)
    assert get_res.status_code == 404

    # 8. Verify user activities has deletion logged
    user_acts = await client.get("/api/v1/activities", headers=headers)
    assert any(a["activity_type"] == "CAMPAIGN_DELETED" for a in user_acts.json())


@pytest.mark.asyncio
async def test_strict_multi_user_isolation(client: AsyncClient):
    """Test 6: User A cannot see, edit, or delete User B's campaigns or activities."""
    # Register User A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "User Alpha",
            "email": "user.a@brand-alpha.com",
            "password": "alphaPassword123",
            "company_name": "Brand Alpha",
        },
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "User Beta",
            "email": "user.b@brand-beta.com",
            "password": "betaPassword123",
            "company_name": "Brand Beta",
        },
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates Campaign A
    camp_a_res = await client.post(
        "/api/v1/campaigns",
        json={
            "name": "Campaign Alpha Secret",
            "brand": "Brand Alpha",
            "budget": 100000,
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
        headers=headers_a,
    )
    camp_a_id = camp_a_res.json()["id"]

    # User B creates Campaign B
    camp_b_res = await client.post(
        "/api/v1/campaigns",
        json={
            "name": "Campaign Beta Secret",
            "brand": "Brand Beta",
            "budget": 300000,
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
        headers=headers_b,
    )
    camp_b_id = camp_b_res.json()["id"]

    # User A lists campaigns -> MUST contain only Campaign A
    list_a = await client.get("/api/v1/campaigns", headers=headers_a)
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["id"] == camp_a_id

    # User B lists campaigns -> MUST contain only Campaign B
    list_b = await client.get("/api/v1/campaigns", headers=headers_b)
    assert len(list_b.json()) == 1
    assert list_b.json()[0]["id"] == camp_b_id

    # User A tries to GET Campaign B -> 404
    get_b_by_a = await client.get(f"/api/v1/campaigns/{camp_b_id}", headers=headers_a)
    assert get_b_by_a.status_code == 404

    # User A tries to PATCH Campaign B -> 404
    patch_b_by_a = await client.patch(
        f"/api/v1/campaigns/{camp_b_id}",
        json={"budget": 999999},
        headers=headers_a,
    )
    assert patch_b_by_a.status_code == 404

    # User A tries to DELETE Campaign B -> 404
    del_b_by_a = await client.delete(f"/api/v1/campaigns/{camp_b_id}", headers=headers_a)
    assert del_b_by_a.status_code == 404

    # User A tries to view Campaign B activities -> 404
    acts_b_by_a = await client.get(f"/api/v1/campaigns/{camp_b_id}/activities", headers=headers_a)
    assert acts_b_by_a.status_code == 404

    # Check Dashboard summaries
    summary_a = await client.get("/api/v1/dashboard/summary", headers=headers_a)
    assert summary_a.json()["total_campaigns"] == 1
    summary_b = await client.get("/api/v1/dashboard/summary", headers=headers_b)
    assert summary_b.json()["total_campaigns"] == 1


@pytest.mark.asyncio
async def test_session_persistence_after_login(client: AsyncClient):
    """Test 7: Campaign data persists across login sessions from PostgreSQL."""
    # 1. Register & create campaign
    email = "persistence@glownaturals.com"
    pwd = "persistPassword123"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Persist User", "email": email, "password": pwd},
    )
    token1 = reg_res.json()["access_token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    create_res = await client.post(
        "/api/v1/campaigns",
        json={
            "name": "Persisted Autumn Launch",
            "brand": "GlowNaturals",
            "budget": 180000,
            "start_date": "2026-10-01",
            "end_date": "2026-11-01",
        },
        headers=h1,
    )
    camp_id = create_res.json()["id"]

    # 2. Login again to get new session token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_res.status_code == 200
    token2 = login_res.json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}

    # 3. Fetch campaign with new session
    get_res = await client.get(f"/api/v1/campaigns/{camp_id}", headers=h2)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Persisted Autumn Launch"
