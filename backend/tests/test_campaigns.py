import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_campaign_crud_lifecycle(client: AsyncClient):
    # 1. Register & get auth token
    reg_payload = {
        "full_name": "Campaign Manager",
        "email": "camp.manager@glownaturals.com",
        "password": "securePassword456",
        "company_name": "GlowNaturals",
        "role": "marketing_manager",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create campaign
    create_payload = {
        "name": "Serum Launch Q4",
        "brand": "GlowNaturals",
        "budget": 250000,
        "objective": "Product Launch",
        "start_date": "2026-10-01",
        "end_date": "2026-11-01",
        "status": "active",
        "health": "excellent",
    }
    create_res = await client.post("/api/v1/campaigns", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    camp_data = create_res.json()
    camp_id = camp_data["id"]
    assert camp_data["name"] == "Serum Launch Q4"
    assert camp_data["budget"] == 250000

    # 3. List campaigns
    list_res = await client.get("/api/v1/campaigns", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Get campaign by ID
    get_res = await client.get(f"/api/v1/campaigns/{camp_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == camp_id

    # 5. Update campaign
    patch_res = await client.patch(
        f"/api/v1/campaigns/{camp_id}",
        json={"spend": 50000, "revenue": 160000, "roas": 3.2},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["roas"] == 3.2


@pytest.mark.asyncio
async def test_influencers_and_approvals(client: AsyncClient):
    reg_payload = {
        "full_name": "Demo Reviewer",
        "email": "reviewer@glownaturals.com",
        "password": "securePassword456",
        "company_name": "GlowNaturals",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List influencers
    inf_res = await client.get("/api/v1/influencers", headers=headers)
    assert inf_res.status_code == 200

    # List approvals
    appr_res = await client.get("/api/v1/approvals", headers=headers)
    assert appr_res.status_code == 200
