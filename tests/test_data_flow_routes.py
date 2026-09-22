import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def make_payload(**overrides):
    payload = {
        "source_urn": "urn:data:postgresql:commerce-prod.public.orders",
        "target_urn": "urn:data:bigquery:test-project.sales.orders",
        "transformation": "teste",
    }
    payload.update(overrides)
    return payload


async def test_create_data_flow(client: AsyncClient) -> None:
    response = await client.post("/data_flows", json=make_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["source_urn"] == "urn:data:postgresql:commerce-prod.public.orders"
    assert body["active"] is True
    assert "id" in body


async def test_list_data_flows(client: AsyncClient) -> None:
    await client.post("/data_flows", json=make_payload())
    await client.post("/data_flows", json=make_payload(transformation=None))

    response = await client.get("/data_flows")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_update_data_flow_deactivates(client: AsyncClient) -> None:
    created = await client.post("/data_flows", json=make_payload())
    flow_id = created.json()["id"]

    response = await client.patch(f"/data_flows/{flow_id}", json={"active": False})

    assert response.status_code == 200
    assert response.json()["active"] is False


async def test_delete_data_flow(client: AsyncClient) -> None:
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
