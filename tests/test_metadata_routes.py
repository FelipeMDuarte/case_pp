import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def make_payload(**overrides):
    payload = {
        "urn": "urn:data:bigquery:test-project.sales.orders",
        "asset": {
            "name": "orders",
            "asset_type": "TABLE",
            "environment": "PRODUCTION",
        },
        "source": {
            "platform": "BIGQUERY",
            "fully_qualified_name": "test-project.sales.orders",
        },
        "ownership": {
            "technical_owner": {
                "type": "TEAM",
                "name": "Data Engineering",
                "contact": "data-engineering@example.com",
            }
        },
    }
    payload.update(overrides)
    return payload


async def test_create_metadata(client: AsyncClient) -> None:
    response = await client.post("/metadata", json=make_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["urn"] == "urn:data:bigquery:test-project.sales.orders"
    assert body["asset"]["name"] == "orders"
    assert "id" in body
    assert "created_at" in body


async def test_create_metadata_logs_audit_event(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())

    response = await client.get("/audit_events")

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "CREATED"
    assert events[0]["metadata_urn"] == "urn:data:bigquery:test-project.sales.orders"


async def test_list_metadata(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.a"))
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.b"))

    response = await client.get("/metadata")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_metadata_not_found(client: AsyncClient) -> None:
    response = await client.get("/metadata/000000000000000000000000")

    assert response.status_code == 404


async def test_create_metadata_missing_required_field(client: AsyncClient) -> None:
    payload = make_payload()
    del payload["source"]

    response = await client.post("/metadata", json=payload)

    assert response.status_code == 422


async def test_list_metadata_pagination(client: AsyncClient) -> None:
    for i in range(3):
        await client.post("/metadata", json=make_payload(urn=f"urn:data:bigquery:test-project.sales.{i}"))

    response = await client.get("/metadata", params={"skip": 1, "limit": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_metadata(client: AsyncClient) -> None:
    created = await client.post("/metadata", json=make_payload())
    metadata_id = created.json()["id"]

    response = await client.get(f"/metadata/{metadata_id}")

    assert response.status_code == 200
    assert response.json()["asset"]["name"] == "orders"


async def test_update_metadata(client: AsyncClient) -> None:
    created = await client.post("/metadata", json=make_payload())
    metadata_id = created.json()["id"]

    response = await client.patch(
        f"/metadata/{metadata_id}",
        json={"security_and_privacy": {"sensitivity": "RESTRICTED"}},
    )

    assert response.status_code == 200
    assert response.json()["security_and_privacy"]["sensitivity"] == "RESTRICTED"
    assert response.json()["asset"]["name"] == "orders"


async def test_update_metadata_logs_audit_event(client: AsyncClient) -> None:
    created = await client.post("/metadata", json=make_payload())
    metadata_id = created.json()["id"]

    await client.patch(
        f"/metadata/{metadata_id}",
        json={"security_and_privacy": {"sensitivity": "RESTRICTED"}},
    )

    events = (await client.get("/audit_events")).json()
    update_events = [e for e in events if e["event_type"] == "UPDATED"]
    assert len(update_events) == 1
    assert update_events[0]["changed_fields"] == ["security_and_privacy"]


async def test_empty_patch_does_not_log_audit_event(client: AsyncClient) -> None:
    created = await client.post("/metadata", json=make_payload())
    metadata_id = created.json()["id"]

    response = await client.patch(f"/metadata/{metadata_id}", json={})

    assert response.status_code == 200
    events = (await client.get("/audit_events")).json()
    assert not any(e["event_type"] == "UPDATED" for e in events)


async def test_malformed_id_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/metadata/not-a-valid-id")).status_code == 404
    assert (await client.patch("/metadata/not-a-valid-id", json={})).status_code == 404
    assert (await client.delete("/metadata/not-a-valid-id")).status_code == 404


async def test_delete_metadata(client: AsyncClient) -> None:
    created = await client.post("/metadata", json=make_payload())
    metadata_id = created.json()["id"]

    response = await client.delete(f"/metadata/{metadata_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/metadata/{metadata_id}")
    assert follow_up.status_code == 404

    events = (await client.get("/audit_events")).json()
    assert any(e["event_type"] == "DELETED" for e in events)
