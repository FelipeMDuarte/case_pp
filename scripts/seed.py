import asyncio
import json
import os
from pathlib import Path

import httpx

BASE_URL = os.environ.get("SEED_API_URL", "http://localhost:8000")
FIXTURE_PATH = Path("metadata_sample.json")


def without_generated_fields(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("created_at", "updated_at")}


async def seed() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text())

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        metadata_created = 0
        for doc in fixture["collections"]["metadata"]:
            response = await client.post("/metadata", json=without_generated_fields(doc))
            response.raise_for_status()
            metadata_created += 1
            print(f"metadata criado: {doc['urn']}")

        flows_created = 0
        for doc in fixture["collections"]["data_flows"]:
            response = await client.post("/data_flows", json=without_generated_fields(doc))
            response.raise_for_status()
            flows_created += 1
            print(f"data_flow criado: {doc['source_urn']} -> {doc['target_urn']}")

        audit_count = len((await client.get("/audit_events")).json())

    print(f"\n{metadata_created} metadata, {flows_created} data_flows, {audit_count} audit_events (gerados automaticamente)")


if __name__ == "__main__":
    asyncio.run(seed())
