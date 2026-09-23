def make_metadata_payload(**overrides) -> dict:
    payload = {
        "urn": "urn:data:bigquery:test-project.sales.orders",
        "asset": {"name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION"},
        "source": {"platform": "BIGQUERY", "fully_qualified_name": "test-project.sales.orders"},
        "ownership": {
            "technical_owner": {"type": "TEAM", "name": "Data Engineering", "contact": "data-engineering@example.com"}
        },
    }
    payload.update(overrides)
    return payload
