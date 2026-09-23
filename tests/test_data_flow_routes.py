import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def make_metadata_payload(urn: str) -> dict:
    return {
        "urn": urn,
        "asset": {"name": urn, "asset_type": "TABLE", "environment": "PRODUCTION"},
        "source": {"platform": "BIGQUERY", "fully_qualified_name": urn},
        "ownership": {
            "technical_owner": {"type": "TEAM", "name": "Data Engineering", "contact": "data-engineering@example.com"}
        },
    }


async def create_metadata(client: AsyncClient, urn: str) -> None:
    await client.post("/metadata", json=make_metadata_payload(urn))


async def create_default_metadata_pair(client: AsyncClient) -> None:
    await create_metadata(client, "urn:data:postgresql:commerce-prod.public.orders")
    await create_metadata(client, "urn:data:bigquery:test-project.sales.orders")


def make_payload(**overrides):
    payload = {
        "source_urn": "urn:data:postgresql:commerce-prod.public.orders",
        "target_urn": "urn:data:bigquery:test-project.sales.orders",
        "transformation": "teste",
    }
    payload.update(overrides)
    return payload


async def test_create_data_flow(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)

    response = await client.post("/data_flows", json=make_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["source_urn"] == "urn:data:postgresql:commerce-prod.public.orders"
    assert body["active"] is True
    assert "id" in body


async def test_create_data_flow_with_unknown_urn_is_rejected(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)

    response = await client.post("/data_flows", json=make_payload(target_urn="urn:data:bigquery:does.not.exist"))

    assert response.status_code == 422


async def test_list_data_flows(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)
    await create_metadata(client, "urn:data:bigquery:test-project.sales.customers")

    await client.post("/data_flows", json=make_payload())
    await client.post("/data_flows", json=make_payload(target_urn="urn:data:bigquery:test-project.sales.customers"))

    response = await client.get("/data_flows")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 2


async def test_update_data_flow_deactivates(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)
    created = await client.post("/data_flows", json=make_payload())
    flow_id = created.json()["id"]

    response = await client.patch(f"/data_flows/{flow_id}", json={"active": False})

    assert response.status_code == 200
    assert response.json()["active"] is False


async def test_update_data_flow_rejects_null_active(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)
    created = await client.post("/data_flows", json=make_payload())
    flow_id = created.json()["id"]

    response = await client.patch(f"/data_flows/{flow_id}", json={"active": None})

    assert response.status_code == 422
    follow_up = await client.get(f"/data_flows/{flow_id}")
    assert follow_up.status_code == 200


async def test_delete_data_flow(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)
    created = await client.post("/data_flows", json=make_payload())
    flow_id = created.json()["id"]

    response = await client.delete(f"/data_flows/{flow_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/data_flows/{flow_id}")
    assert follow_up.status_code == 404


async def test_update_data_flow_not_found(client: AsyncClient) -> None:
    response = await client.patch("/data_flows/000000000000000000000000", json={"active": False})

    assert response.status_code == 404


async def test_delete_data_flow_not_found(client: AsyncClient) -> None:
    response = await client.delete("/data_flows/000000000000000000000000")

    assert response.status_code == 404


async def test_create_duplicate_data_flow_is_rejected(client: AsyncClient) -> None:
    await create_default_metadata_pair(client)
    await client.post("/data_flows", json=make_payload())

    response = await client.post("/data_flows", json=make_payload(transformation="outra descrição"))

    assert response.status_code == 409
