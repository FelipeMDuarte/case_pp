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
    "structure": {"columns": [{"name": "order_id", "data_type": "STRING"}]},
}


async def test_schema_versions_are_read_only(client: AsyncClient) -> None:
    await client.post("/metadata", json=metadata_payload)
    versions = (await client.get("/schema_versions")).json()["items"]
    version_id = versions[0]["id"]

    assert (await client.post("/schema_versions", json={})).status_code == 405
    assert (await client.patch(f"/schema_versions/{version_id}", json={})).status_code == 405
    assert (await client.delete(f"/schema_versions/{version_id}")).status_code == 405


async def test_get_schema_version(client: AsyncClient) -> None:
    await client.post("/metadata", json=metadata_payload)
    versions = (await client.get("/schema_versions")).json()["items"]
    version_id = versions[0]["id"]

    response = await client.get(f"/schema_versions/{version_id}")

    assert response.status_code == 200
    assert response.json()["columns"][0]["name"] == "order_id"


async def test_get_schema_version_not_found(client: AsyncClient) -> None:
    response = await client.get("/schema_versions/000000000000000000000000")

    assert response.status_code == 404
