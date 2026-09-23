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


async def test_search_metadata_by_urn(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.a"))
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.b"))

    response = await client.get("/metadata", params={"urn": "urn:data:bigquery:test-project.sales.b"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["urn"] == "urn:data:bigquery:test-project.sales.b"


async def test_search_metadata_by_nested_field(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload(urn="urn:a", asset={"name": "a", "asset_type": "TABLE", "environment": "PRODUCTION", "domain": "SALES"}))
    await client.post("/metadata", json=make_payload(urn="urn:b", asset={"name": "b", "asset_type": "TABLE", "environment": "PRODUCTION", "domain": "MARKETING"}))

    response = await client.get("/metadata", params={"asset.domain": "MARKETING"})

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["urn"] == "urn:b"


async def test_search_metadata_is_case_insensitive_and_partial(client: AsyncClient) -> None:
    await client.post(
        "/metadata",
        json=make_payload(
            urn="urn:data:postgresql:erp-prod.public.compras",
            asset={"name": "compras", "asset_type": "TABLE", "environment": "PRODUCTION"},
            source={"platform": "POSTGRESQL", "fully_qualified_name": "erp-prod.public.compras"},
        ),
    )

    response = await client.get("/metadata", params={"asset.name": "compra", "source.platform": "postgresql"})

    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_search_metadata_treats_input_as_literal_text(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())

    # a busca é substring em Python puro, então ".*" é só texto
    # não deveria casar com nada aqui
    response = await client.get("/metadata", params={"asset.name": ".*"})

    assert response.status_code == 200
    assert response.json() == []


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


async def test_update_metadata_preserves_unsent_nested_fields(client: AsyncClient) -> None:
    payload = make_payload(
        security_and_privacy={"sensitivity": "CONFIDENTIAL", "contains_personal_data": True, "regulations": ["LGPD"]}
    )
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    response = await client.patch(
        f"/metadata/{metadata_id}",
        json={"security_and_privacy": {"sensitivity": "RESTRICTED"}},
    )

    assert response.status_code == 200
    security = response.json()["security_and_privacy"]
    assert security["sensitivity"] == "RESTRICTED"
    assert security["contains_personal_data"] is True
    assert security["regulations"] == ["LGPD"]


async def test_update_metadata_preserves_sibling_fields_not_sent(client: AsyncClient) -> None:
    payload = make_payload(asset={"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION", "tags": ["orders"]})
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    # manda o "asset" de novo sem "tags" — tags não deveria sumir
    response = await client.patch(
        f"/metadata/{metadata_id}",
        json={"asset": {"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION", "layer": "GOLD"}},
    )

    assert response.status_code == 200
    assert response.json()["asset"]["tags"] == ["orders"]
    assert response.json()["asset"]["layer"] == "GOLD"


async def test_update_metadata_with_null_structure_clears_it(client: AsyncClient) -> None:
    payload = make_payload(structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    response = await client.patch(f"/metadata/{metadata_id}", json={"structure": None})

    assert response.status_code == 200
    assert response.json()["structure"] is None

    versions = (await client.get("/schema_versions")).json()
    assert versions[0]["columns"] == []
    assert versions[0]["change_summary"] == "coluna(s) removida(s): order_id"


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


async def test_create_metadata_with_structure_logs_schema_version(client: AsyncClient) -> None:
    payload = make_payload(structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})

    created = await client.post("/metadata", json=payload)
    assert created.status_code == 201

    versions = (await client.get("/schema_versions")).json()
    assert len(versions) == 1
    assert versions[0]["metadata_urn"] == payload["urn"]
    assert versions[0]["columns"] == [{"name": "order_id", "data_type": "STRING", "description": None}]
    assert versions[0]["change_summary"] == "estrutura inicial (1 coluna(s))"


async def test_update_structure_logs_new_schema_version_with_added_column(client: AsyncClient) -> None:
    payload = make_payload(structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    new_structure = {"columns": [{"name": "order_id", "data_type": "STRING"}, {"name": "total", "data_type": "NUMERIC"}]}
    await client.patch(f"/metadata/{metadata_id}", json={"structure": new_structure})

    versions = (await client.get("/schema_versions")).json()
    assert len(versions) == 2
    newest = versions[0]
    assert len(newest["columns"]) == 2
    assert newest["change_summary"] == "coluna(s) adicionada(s): total"


async def test_update_structure_logs_removed_column(client: AsyncClient) -> None:
    payload = make_payload(
        structure={"columns": [{"name": "order_id", "data_type": "STRING"}, {"name": "legacy_flag", "data_type": "BOOLEAN"}]}
    )
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    new_structure = {"columns": [{"name": "order_id", "data_type": "STRING"}]}
    await client.patch(f"/metadata/{metadata_id}", json={"structure": new_structure})

    versions = (await client.get("/schema_versions")).json()
    assert versions[0]["change_summary"] == "coluna(s) removida(s): legacy_flag"


async def test_update_structure_logs_changed_column_type(client: AsyncClient) -> None:
    payload = make_payload(structure={"columns": [{"name": "total", "data_type": "STRING"}]})
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    new_structure = {"columns": [{"name": "total", "data_type": "NUMERIC"}]}
    await client.patch(f"/metadata/{metadata_id}", json={"structure": new_structure})

    versions = (await client.get("/schema_versions")).json()
    assert versions[0]["change_summary"] == "tipo alterado: total"


async def test_unrelated_patch_does_not_log_schema_version(client: AsyncClient) -> None:
    payload = make_payload(structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})
    created = await client.post("/metadata", json=payload)
    metadata_id = created.json()["id"]

    await client.patch(f"/metadata/{metadata_id}", json={"security_and_privacy": {"sensitivity": "RESTRICTED"}})

    versions = (await client.get("/schema_versions")).json()
    assert len(versions) == 1


async def test_create_metadata_without_structure_does_not_log_schema_version(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())

    versions = (await client.get("/schema_versions")).json()
    assert versions == []


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
