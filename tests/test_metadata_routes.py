import pytest
from httpx import AsyncClient

from tests.factories import make_metadata_payload as make_payload

pytestmark = pytest.mark.asyncio


async def create_metadata(client: AsyncClient, **overrides) -> str:
    response = await client.post("/metadata", json=make_payload(**overrides))
    return response.json()["id"]


async def test_create_metadata(client: AsyncClient) -> None:
    response = await client.post("/metadata", json=make_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["urn"] == "urn:data:bigquery:test-project.sales.orders"
    assert body["asset"]["name"] == "orders"
    assert "id" in body
    assert "created_at" in body
    assert response.headers["location"] == f"/metadata/{body['id']}"


async def test_create_metadata_logs_audit_event(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())

    response = await client.get("/audit_events")

    assert response.status_code == 200
    events = response.json()["items"]
    assert len(events) == 1
    assert events[0]["event_type"] == "CREATED"
    assert events[0]["metadata_urn"] == "urn:data:bigquery:test-project.sales.orders"


async def test_list_metadata(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.a"))
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.b"))

    response = await client.get("/metadata")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 2


async def test_get_metadata_not_found(client: AsyncClient) -> None:
    response = await client.get("/metadata/000000000000000000000000")

    assert response.status_code == 404


async def test_create_metadata_missing_required_field(client: AsyncClient) -> None:
    payload = make_payload()
    del payload["source"]

    response = await client.post("/metadata", json=payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert "source" in response.json()["detail"]


async def test_create_metadata_rejects_invalid_enum_value(client: AsyncClient) -> None:
    payload = make_payload(asset={"name": "orders", "asset_type": "NOT_A_REAL_TYPE", "environment": "PRODUCTION"})

    response = await client.post("/metadata", json=payload)

    assert response.status_code == 422


async def test_create_metadata_rejects_out_of_range_score(client: AsyncClient) -> None:
    payload = make_payload(
        quality={"status": "PASSED", "score": 1.5, "checked_at": "2026-01-01T00:00:00Z", "issues": []}
    )

    response = await client.post("/metadata", json=payload)

    assert response.status_code == 422


async def test_list_metadata_pagination(client: AsyncClient) -> None:
    for i in range(3):
        await client.post("/metadata", json=make_payload(urn=f"urn:data:bigquery:test-project.sales.{i}"))

    response = await client.get("/metadata", params={"skip": 1, "limit": 1})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["total"] == 3


async def test_list_metadata_pagination_pages_do_not_overlap(client: AsyncClient) -> None:
    for i in range(5):
        await client.post("/metadata", json=make_payload(urn=f"urn:data:bigquery:test-project.sales.t{i}"))

    page1 = (await client.get("/metadata", params={"skip": 0, "limit": 2})).json()["items"]
    page2 = (await client.get("/metadata", params={"skip": 2, "limit": 2})).json()["items"]
    page3 = (await client.get("/metadata", params={"skip": 4, "limit": 2})).json()["items"]

    urns_by_page = [{item["urn"] for item in page} for page in (page1, page2, page3)]
    assert [len(page) for page in urns_by_page] == [2, 2, 1]
    assert urns_by_page[0] & urns_by_page[1] == set()
    assert urns_by_page[1] & urns_by_page[2] == set()
    assert set.union(*urns_by_page) == {f"urn:data:bigquery:test-project.sales.t{i}" for i in range(5)}


async def test_list_metadata_rejects_negative_skip(client: AsyncClient) -> None:
    response = await client.get("/metadata", params={"skip": -1})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


async def test_list_metadata_rejects_limit_above_max(client: AsyncClient) -> None:
    response = await client.get("/metadata", params={"limit": 101})

    assert response.status_code == 422


async def test_search_metadata_by_urn(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.a"))
    await client.post("/metadata", json=make_payload(urn="urn:data:bigquery:test-project.sales.b"))

    response = await client.get("/metadata", params={"urn": "urn:data:bigquery:test-project.sales.b"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["urn"] == "urn:data:bigquery:test-project.sales.b"


async def test_search_metadata_by_nested_field(client: AsyncClient) -> None:
    asset_a = {"name": "a", "asset_type": "TABLE", "environment": "PRODUCTION", "domain": "SALES"}
    asset_b = {"name": "b", "asset_type": "TABLE", "environment": "PRODUCTION", "domain": "MARKETING"}
    await client.post("/metadata", json=make_payload(urn="urn:a", asset=asset_a))
    await client.post("/metadata", json=make_payload(urn="urn:b", asset=asset_b))

    response = await client.get("/metadata", params={"asset.domain": "MARKETING"})

    assert response.status_code == 200
    results = response.json()["items"]
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
    assert len(response.json()["items"]) == 1


async def test_search_metadata_treats_input_as_literal_text(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())
    response = await client.get("/metadata", params={"asset.name": ".*"})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_get_metadata(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    response = await client.get(f"/metadata/{metadata_id}")

    assert response.status_code == 200
    assert response.json()["asset"]["name"] == "orders"


async def test_update_metadata(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    response = await client.patch(
        f"/metadata/{metadata_id}",
        json={"security_and_privacy": {"sensitivity": "RESTRICTED"}},
    )

    assert response.status_code == 200
    assert response.json()["security_and_privacy"]["sensitivity"] == "RESTRICTED"
    assert response.json()["asset"]["name"] == "orders"


async def test_update_metadata_preserves_unsent_nested_fields(client: AsyncClient) -> None:
    metadata_id = await create_metadata(
        client,
        security_and_privacy={"sensitivity": "CONFIDENTIAL", "contains_personal_data": True, "regulations": ["LGPD"]},
    )

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
    metadata_id = await create_metadata(
        client, asset={"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION", "tags": ["orders"]}
    )

    response = await client.patch(
        f"/metadata/{metadata_id}",
        json={"asset": {"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION", "layer": "GOLD"}},
    )

    assert response.status_code == 200
    assert response.json()["asset"]["tags"] == ["orders"]
    assert response.json()["asset"]["layer"] == "GOLD"


async def test_update_metadata_with_null_structure_clears_it(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client, structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})

    response = await client.patch(f"/metadata/{metadata_id}", json={"structure": None})

    assert response.status_code == 200
    assert response.json()["structure"] is None

    versions = (await client.get("/schema_versions")).json()["items"]
    assert versions[0]["columns"] == []
    assert versions[0]["change_summary"] == "coluna(s) removida(s): order_id"


async def test_update_rejects_null_on_required_blocks(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    for field in ("asset", "source", "ownership"):
        response = await client.patch(f"/metadata/{metadata_id}", json={field: None})
        assert response.status_code == 422, field

    # o registro não pode ter sido corrompido pelas tentativas acima
    follow_up = await client.get(f"/metadata/{metadata_id}")
    assert follow_up.status_code == 200


async def test_update_asset_partial_preserves_other_asset_fields(client: AsyncClient) -> None:
    metadata_id = await create_metadata(
        client, asset={"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION", "tags": ["orders"]}
    )

    response = await client.patch(f"/metadata/{metadata_id}", json={"asset": {"status": "INACTIVE"}})

    assert response.status_code == 200
    asset = response.json()["asset"]
    assert asset["status"] == "INACTIVE"
    assert asset["name"] == "orders"
    assert asset["tags"] == ["orders"]


async def test_update_sets_nested_field_that_was_previously_null(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    response = await client.patch(
        f"/metadata/{metadata_id}",
        json={"ownership": {"business_owner": {"type": "PERSON", "name": "Ana", "contact": "ana@example.com"}}},
    )

    assert response.status_code == 200
    ownership = response.json()["ownership"]
    assert ownership["business_owner"] == {"type": "PERSON", "name": "Ana", "contact": "ana@example.com"}
    assert ownership["technical_owner"]["name"] == "Data Engineering"


async def test_update_rejects_incomplete_block_that_was_previously_null(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    # quality nunca foi setado (é null); mandar só um campo não dá pra formar um Quality válido
    response = await client.patch(f"/metadata/{metadata_id}", json={"quality": {"score": 0.8}})

    assert response.status_code == 422
    follow_up = await client.get(f"/metadata/{metadata_id}")
    assert follow_up.json()["quality"] is None


async def test_update_metadata_logs_audit_event(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    await client.patch(
        f"/metadata/{metadata_id}",
        json={"security_and_privacy": {"sensitivity": "RESTRICTED"}},
    )

    events = (await client.get("/audit_events")).json()["items"]
    update_events = [e for e in events if e["event_type"] == "UPDATED"]
    assert len(update_events) == 1
    assert update_events[0]["changed_fields"] == ["security_and_privacy"]


async def test_empty_patch_does_not_log_audit_event(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    response = await client.patch(f"/metadata/{metadata_id}", json={})

    assert response.status_code == 200
    events = (await client.get("/audit_events")).json()["items"]
    assert not any(e["event_type"] == "UPDATED" for e in events)


async def test_create_metadata_with_structure_logs_schema_version(client: AsyncClient) -> None:
    payload = make_payload(structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})

    created = await client.post("/metadata", json=payload)
    assert created.status_code == 201

    versions = (await client.get("/schema_versions")).json()["items"]
    assert len(versions) == 1
    assert versions[0]["metadata_urn"] == payload["urn"]
    assert versions[0]["columns"] == [{"name": "order_id", "data_type": "STRING", "description": None}]
    assert versions[0]["change_summary"] == "estrutura inicial (1 coluna(s))"


async def test_update_structure_logs_new_schema_version_with_added_column(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client, structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})

    new_structure = {"columns": [{"name": "order_id", "data_type": "STRING"}, {"name": "total", "data_type": "NUMERIC"}]}
    await client.patch(f"/metadata/{metadata_id}", json={"structure": new_structure})

    versions = (await client.get("/schema_versions")).json()["items"]
    assert len(versions) == 2
    newest = versions[0]
    assert len(newest["columns"]) == 2
    assert newest["change_summary"] == "coluna(s) adicionada(s): total"


async def test_update_structure_logs_removed_column(client: AsyncClient) -> None:
    metadata_id = await create_metadata(
        client,
        structure={"columns": [{"name": "order_id", "data_type": "STRING"}, {"name": "legacy_flag", "data_type": "BOOLEAN"}]},
    )

    new_structure = {"columns": [{"name": "order_id", "data_type": "STRING"}]}
    await client.patch(f"/metadata/{metadata_id}", json={"structure": new_structure})

    versions = (await client.get("/schema_versions")).json()["items"]
    assert versions[0]["change_summary"] == "coluna(s) removida(s): legacy_flag"


async def test_update_structure_logs_changed_column_type(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client, structure={"columns": [{"name": "total", "data_type": "STRING"}]})

    new_structure = {"columns": [{"name": "total", "data_type": "NUMERIC"}]}
    await client.patch(f"/metadata/{metadata_id}", json={"structure": new_structure})

    versions = (await client.get("/schema_versions")).json()["items"]
    assert versions[0]["change_summary"] == "tipo alterado: total"


async def test_unrelated_patch_does_not_log_schema_version(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client, structure={"columns": [{"name": "order_id", "data_type": "STRING"}]})

    await client.patch(f"/metadata/{metadata_id}", json={"security_and_privacy": {"sensitivity": "RESTRICTED"}})

    versions = (await client.get("/schema_versions")).json()["items"]
    assert len(versions) == 1


async def test_create_metadata_without_structure_does_not_log_schema_version(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())

    versions = (await client.get("/schema_versions")).json()["items"]
    assert versions == []


async def test_create_duplicate_urn_is_rejected(client: AsyncClient) -> None:
    await client.post("/metadata", json=make_payload())

    response = await client.post("/metadata", json=make_payload())

    assert response.status_code == 409


async def test_malformed_id_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/metadata/not-a-valid-id")).status_code == 404
    assert (await client.patch("/metadata/not-a-valid-id", json={})).status_code == 404
    assert (await client.delete("/metadata/not-a-valid-id")).status_code == 404


async def test_delete_metadata_is_a_soft_delete(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    response = await client.delete(f"/metadata/{metadata_id}")
    assert response.status_code == 204

    follow_up = await client.get(f"/metadata/{metadata_id}")
    assert follow_up.status_code == 200
    assert follow_up.json()["asset"]["status"] == "DEPRECATED"

    events = (await client.get("/audit_events")).json()["items"]
    assert any(e["event_type"] == "DELETED" for e in events)


async def test_delete_already_deprecated_metadata_returns_410(client: AsyncClient) -> None:
    metadata_id = await create_metadata(client)

    first = await client.delete(f"/metadata/{metadata_id}")
    assert first.status_code == 204

    second = await client.delete(f"/metadata/{metadata_id}")
    assert second.status_code == 410


async def test_delete_metadata_referenced_by_data_flow_does_not_orphan_it(client: AsyncClient) -> None:
    source_id = await create_metadata(client, urn="urn:data:bigquery:test-project.sales.source")
    await create_metadata(client, urn="urn:data:bigquery:test-project.sales.target")
    await client.post(
        "/data_flows",
        json={
            "source_urn": "urn:data:bigquery:test-project.sales.source",
            "target_urn": "urn:data:bigquery:test-project.sales.target",
        },
    )

    response = await client.delete(f"/metadata/{source_id}")
    assert response.status_code == 204

    flows = (await client.get("/data_flows")).json()["items"]
    assert flows[0]["source_urn"] == "urn:data:bigquery:test-project.sales.source"
