import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


metadata_payload = {
    "urn": "urn:data:bigquery:test-project.sales.orders",
    "asset": {"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION"},
    "source": {"platform": "BIGQUERY", "fully_qualified_name": "test-project.sales.orders"},
    "ownership": {
        "technical_owner": {"type": "TEAM", "name": "Data Engineering", "contact": "data-engineering@example.com"}
    },
}


async def test_audit_events_are_read_only(client: AsyncClient) -> None:
    await client.post("/metadata", json=metadata_payload)
    events = (await client.get("/audit_events")).json()["items"]
    event_id = events[0]["id"]

    # audit_events não tem POST/PATCH/DELETE
    assert (await client.post("/audit_events", json={})).status_code == 405
    assert (await client.patch(f"/audit_events/{event_id}", json={})).status_code == 405
    assert (await client.delete(f"/audit_events/{event_id}")).status_code == 405


async def test_get_audit_event(client: AsyncClient) -> None:
    await client.post("/metadata", json=metadata_payload)
    events = (await client.get("/audit_events")).json()["items"]
    event_id = events[0]["id"]

    response = await client.get(f"/audit_events/{event_id}")

    assert response.status_code == 200
    assert response.json()["event_type"] == "CREATED"


async def test_get_audit_event_not_found(client: AsyncClient) -> None:
    response = await client.get("/audit_events/000000000000000000000000")

    assert response.status_code == 404
